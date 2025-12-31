import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from archive_manager import ArchiveManager
from config import Config
from instagram_api import InstagramAPI
from media_manager import MediaManager
from twitter_api import TwitterAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class StoryArchiver:
    def __init__(self, config: Config):
        self.config = config
        self.instagram_api = InstagramAPI(config)
        self.twitter_api = TwitterAPI(config)
        self.media_manager = MediaManager(config.MEDIA_CACHE_DIR)
        self.archive_manager = ArchiveManager(
            config.ARCHIVE_DB_PATH,
            default_instagram_username=config.INSTAGRAM_USERNAME,
        )

    def _format_story_datetime(self, taken_at: int) -> str:
        """Format Unix timestamp to human-readable datetime in GMT+7 timezone."""
        utc_plus_7 = timezone(timedelta(hours=7))
        dt = datetime.fromtimestamp(taken_at, tz=utc_plus_7)
        return dt.strftime("%A, %d %B %Y %H:%M")

    def _ensure_anchor_tweet(self, instagram_username: str) -> Optional[str]:
        """Ensure the anchor tweet exists for a given Instagram account."""
        username = instagram_username.strip().lstrip('@')
        anchor_id = self.archive_manager.get_anchor_tweet_id(username)

        if anchor_id:
            logger.info(f"Using existing anchor tweet for {username}: {anchor_id}")
            return anchor_id

        logger.info(f"Creating anchor tweet for {username}...")
        anchor_text = self.config.get_anchor_text(username)
        anchor_id = self.twitter_api.post_tweet(anchor_text)

        if not anchor_id:
            logger.error(f"Failed to create anchor tweet for {username}")
            return None

        self.archive_manager.set_anchor_tweet_id(username, anchor_id)
        self.archive_manager.set_last_tweet_id(username, anchor_id)
        logger.info(f"Anchor tweet created for {username}: {anchor_id}")
        return anchor_id

    def archive_story(self, username: str, story_id: str, story_payload: Optional[Dict] = None) -> bool:
        """Download media and save story to archive without posting to Twitter."""
        username = username.strip().lstrip('@')
        try:
            story_id = str(story_id)
            logger.info(f"=== Starting archive_story for {story_id} from {username} ===")

            # Check if already archived
            archived_ids = self.archive_manager.get_archived_story_ids(username)
            if story_id in archived_ids:
                logger.info(f"Story {story_id} already archived for {username}, skipping")
                return False

            # Fetch story data if not provided
            story_data = (
                story_payload
                if story_payload is not None
                else self.instagram_api.get_story_by_id(username, story_id)
            )
            if not story_data:
                logger.error(f"Failed to fetch story {story_id} from {username}")
                return False

            taken_at = int(story_data.get('taken_at', 0) or 0)
            media_list = self.instagram_api.extract_media_urls(story_data)
            if not media_list:
                logger.warning(f"No media found in story {story_id}")
                return False

            # Download and prepare media
            media = media_list[0]
            media_path = self.media_manager.download_media(
                media['url'],
                f"{username}_{story_id}_0",
                media['type'],
            )
            if not media_path:
                logger.error(f"Failed to download media for story {story_id}")
                return False

            if media['type'] == 'image':
                media_path = self.media_manager.compress_image(media_path)

            # Save to archive
            archive_data = {
                'media_count': len(media_list),
                'media_urls': [m['url'] for m in media_list],
                'tweet_ids': [],  # Not posted yet
                'taken_at': taken_at,
                'local_media_path': media_path,
                'media_type': media['type'],
            }
            self.archive_manager.add_story(username, story_id, archive_data)
            
            logger.info(f"Successfully archived story {story_id} for {username} (local: {media_path})")
            return True
        except Exception as e:
            logger.error(f"Error archiving story {story_id}: {e}", exc_info=True)
            return False

    def post_story(self, username: str, story_id: str) -> bool:
        """Post an archived story to Twitter."""
        username = username.strip().lstrip('@')
        try:
            story_id = str(story_id)
            logger.info(f"=== Starting post_story for {story_id} from {username} ===")

            # Get story from archive
            stats = self.archive_manager.get_statistics(username)
            stories = stats.get('stories', [])
            story_entry = next((s for s in stories if str(s.get('story_id')) == story_id), None)

            if not story_entry:
                logger.error(f"Story {story_id} not found in archive for {username}")
                return False

            if story_entry.get('tweet_ids'):
                logger.info(f"Story {story_id} already posted for {username}")
                return True

            media_path = story_entry.get('local_media_path')
            if not media_path or not os.path.exists(media_path):
                logger.info(f"Local media missing for {story_id}, attempting re-download...")
                media_urls = story_entry.get('media_urls', [])
                media_type = story_entry.get('media_type', 'image')
                if not media_urls:
                    logger.error(f"No media URLs available to re-download story {story_id}")
                    return False
                
                media_path = self.media_manager.download_media(
                    media_urls[0],
                    f"{username}_{story_id}_0",
                    media_type,
                )
                if not media_path:
                    logger.error(f"Failed to re-download media for story {story_id}")
                    return False
                
                if media_type == 'image':
                    media_path = self.media_manager.compress_image(media_path)

            # Ensure anchor tweet
            anchor_id = self._ensure_anchor_tweet(username)
            if not anchor_id:
                logger.error("Cannot proceed without anchor tweet")
                return False

            # Prepare caption
            taken_at = story_entry.get('taken_at')
            caption = self.config.get_story_caption(username, taken_at)
            
            last_tweet_id = self.archive_manager.get_last_tweet_id(username) or anchor_id

            # Upload and post
            media_id = self.twitter_api.upload_media(media_path)
            if not media_id:
                logger.error(f"Failed to upload media for story {story_id}")
                return False

            tweet_id = self.twitter_api.post_tweet(
                text=caption,
                media_ids=[media_id],
                reply_to_id=last_tweet_id,
            )

            if not tweet_id:
                logger.error(f"Failed to post tweet for story {story_id}")
                return False

            # Update archive
            self.archive_manager.update_story_tweets(username, story_id, [tweet_id])
            self.archive_manager.set_last_tweet_id(username, tweet_id)
            self.archive_manager.update_story_local_path(username, story_id, None)

            # Cleanup
            self.media_manager.cleanup_media(media_path)

            logger.info(f"Successfully posted story {story_id} for {username}")
            return True
        except Exception as e:
            logger.error(f"Error posting story {story_id}: {e}", exc_info=True)
            return False

    def process_story(self, username: str, story_id: str, story_payload: Optional[Dict] = None) -> bool:
        """Process a single story immediately: archive and post."""
        if self.archive_story(username, story_id, story_payload):
            return self.post_story(username, story_id)
        return False

    def archive_all_stories_for_user(self, username: str) -> int:
        """Fetch and archive all available stories for the given username."""
        username = username.strip().lstrip('@')

        try:
            logger.info(f"Starting story check for {username}")

            stories = self.instagram_api.get_user_stories(username)
            if stories is None:
                logger.error(f"Failed to fetch stories from Instagram API for {username}")
                return 0

            if not isinstance(stories, list):
                logger.error(f"Expected list from Instagram API, got {type(stories)}: {stories}")
                return 0

            story_items = [story for story in stories if isinstance(story, dict)]
            if len(story_items) != len(stories):
                logger.warning(f"Some stories are not dictionaries: {len(story_items)}/{len(stories)} are valid")

            def _story_timestamp(item: Dict) -> int:
                value = item.get('taken_at') or 0
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 0

            story_items.sort(key=_story_timestamp)
            logger.info(f"Found {len(story_items)} stories to evaluate for {username}")

            archived_ids = self.archive_manager.get_archived_story_ids(username)
            processed_count = 0

            if not story_items:
                logger.info(f"No active stories available for {username} at this time")

            for i, story in enumerate(story_items):
                story_id = story.get('pk') or story.get('id')
                if not story_id:
                    logger.debug(f"Skipping story {i} without an ID")
                    continue

                story_id_str = str(story_id)
                logger.info(f"Processing story {i + 1}/{len(story_items)} for {username}: {story_id_str}")

                if story_id_str in archived_ids:
                    logger.info(f"Story {story_id_str} already archived for {username}, skipping")
                    continue

                success = self.archive_story(username, story_id_str, story_payload=story)
                logger.info(f"Story {story_id_str} archiving result for {username}: {success}")

                if success:
                    processed_count += 1
                    archived_ids.add(story_id_str)

            logger.info(f"Story check completed for {username}")
            logger.info(f"New stories archived for {username}: {processed_count}")
            return processed_count

        except Exception as e:
            logger.error(f"Error archiving stories for {username}: {e}", exc_info=True)
            return 0

    def archive_all_stories(self) -> int:
        """Fetch and archive all available stories for all configured usernames."""
        total_processed = 0
        for username in self.config.INSTAGRAM_USERNAMES:
            total_processed += self.archive_all_stories_for_user(username)
        return total_processed

    def post_pending_stories(self) -> int:
        """Post all pending stories that meet the 'next day' criteria."""
        total_posted = 0
        
        # Calculate the start of today in GMT+7
        now = datetime.now(timezone(timedelta(hours=7)))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Checking for pending stories taken before {today_start}")

        for username in self.config.INSTAGRAM_USERNAMES:
            username = username.strip().lstrip('@')
            stats = self.archive_manager.get_statistics(username)
            stories = stats.get('stories', [])
            
            # Filter pending stories (not posted yet)
            pending = [s for s in stories if not s.get('tweet_ids')]
            
            # Sort by taken_at
            pending.sort(key=lambda x: int(x.get('taken_at', 0)))
            
            for story in pending:
                taken_at = int(story.get('taken_at', 0))
                taken_at_dt = datetime.fromtimestamp(taken_at, tz=timezone(timedelta(hours=7)))
                
                if taken_at_dt < today_start:
                    logger.info(f"Posting pending story {story.get('story_id')} for {username} (taken at {taken_at_dt})")
                    if self.post_story(username, story.get('story_id')):
                        total_posted += 1
                else:
                    logger.info(f"Story {story.get('story_id')} for {username} is from today ({taken_at_dt}), skipping")

        self.media_manager.cleanup_old_media()
        return total_posted

    def print_status(self) -> None:
        stats = self.archive_manager.get_statistics()

        logger.info("=" * 50)
        logger.info("ARCHIVE STATUS")
        logger.info(f"Total Stories (all accounts): {stats.get('total_stories')}")
        logger.info(f"Total Media Items (all accounts): {stats.get('total_media')}")

        accounts = stats.get('accounts') or {}
        for username, account_stats in accounts.items():
            logger.info("-" * 50)
            logger.info(f"Instagram: {username}")
            logger.info(f"  Stories: {account_stats.get('total_stories')}")
            logger.info(f"  Media:   {account_stats.get('total_media')}")
            logger.info(f"  Last check: {account_stats.get('last_check')}")
            logger.info(f"  Anchor tweet: {account_stats.get('anchor_tweet_id')}")
            logger.info(f"  Last tweet:   {account_stats.get('last_tweet_id')}")

        logger.info("=" * 50)
