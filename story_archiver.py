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

            # Download and prepare ALL media items
            local_media_paths = []
            media_types = []
            
            for idx, media in enumerate(media_list):
                media_path = self.media_manager.download_media(
                    media['url'],
                    f"{username}_{story_id}_{idx}",
                    media['type'],
                )
                if not media_path:
                    logger.warning(f"Failed to download media {idx} for story {story_id}, continuing with others")
                    continue

                if media['type'] == 'image':
                    media_path = self.media_manager.compress_image(media_path)
                
                local_media_paths.append(media_path)
                media_types.append(media['type'])
            
            if not local_media_paths:
                logger.error(f"Failed to download any media for story {story_id}")
                return False
            
            logger.info(f"Downloaded {len(local_media_paths)} media items for story {story_id}")

            # Save to archive with all media paths
            archive_data = {
                'media_count': len(media_list),
                'media_urls': [m['url'] for m in media_list],
                'tweet_ids': [],  # Not posted yet
                'taken_at': taken_at,
                'local_media_paths': local_media_paths,
                'media_types': media_types,
                # Keep legacy fields for backward compatibility
                'local_media_path': local_media_paths[0] if local_media_paths else None,
                'media_type': media_types[0] if media_types else 'image',
            }
            self.archive_manager.add_story(username, story_id, archive_data)
            
            logger.info(f"Successfully archived story {story_id} for {username} with {len(local_media_paths)} media items")
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

            # Get all media paths (new format) or fallback to single path (legacy)
            media_paths = story_entry.get('local_media_paths', [])
            media_types = story_entry.get('media_types', [])
            
            # Fallback to legacy single media format
            if not media_paths:
                legacy_path = story_entry.get('local_media_path')
                legacy_type = story_entry.get('media_type', 'image')
                if legacy_path:
                    media_paths = [legacy_path]
                    media_types = [legacy_type]
            
            # Check if media exists or needs re-download
            valid_paths = [p for p in media_paths if p and os.path.exists(p)]
            
            if not valid_paths:
                logger.info(f"Local media missing for {story_id}, attempting re-download...")
                media_urls = story_entry.get('media_urls', [])
                if not media_urls:
                    logger.error(f"No media URLs available to re-download story {story_id}")
                    return False
                
                # Get stored media types if available, otherwise detect from URL
                stored_media_types = story_entry.get('media_types', [])
                
                # Re-download all media
                media_paths = []
                media_types = []
                for idx, url in enumerate(media_urls):
                    # Use stored media type if available, otherwise detect from URL
                    if idx < len(stored_media_types) and stored_media_types[idx]:
                        media_type = stored_media_types[idx]
                    else:
                        media_type = 'video' if 'video' in url.lower() else 'image'
                    
                    media_path = self.media_manager.download_media(
                        url,
                        f"{username}_{story_id}_{idx}",
                        media_type,
                    )
                    if not media_path:
                        logger.warning(f"Failed to re-download media {idx} for story {story_id}")
                        continue
                    
                    if media_type == 'image':
                        media_path = self.media_manager.compress_image(media_path)
                    
                    media_paths.append(media_path)
                    media_types.append(media_type)
                
                if not media_paths:
                    logger.error(f"Failed to re-download any media for story {story_id}")
                    return False
            else:
                media_paths = valid_paths

            # Ensure anchor tweet
            anchor_id = self._ensure_anchor_tweet(username)
            if not anchor_id:
                logger.error("Cannot proceed without anchor tweet")
                return False

            # Prepare caption
            taken_at = story_entry.get('taken_at')
            caption = self.config.get_story_caption(username, taken_at)
            
            last_tweet_id = self.archive_manager.get_last_tweet_id(username) or anchor_id
            
            # Post all media as a thread
            # Twitter allows up to 4 media items (images/videos) per tweet
            tweet_ids = []
            
            # Prepare batches of media (up to 4 items per tweet)
            media_batches = [media_paths[i:i + 4] for i in range(0, len(media_paths), 4)]
            
            # Post each batch as a tweet
            for idx, batch_paths in enumerate(media_batches):
                # Upload all media in batch
                media_ids = []
                for path in batch_paths:
                    media_id = self.twitter_api.upload_media(path)
                    if media_id:
                        media_ids.append(media_id)
                
                if not media_ids:
                    logger.error(f"Failed to upload media batch {idx + 1} for story {story_id}")
                    continue
                
                # Add batch info to caption if there are multiple batches
                if len(media_batches) > 1:
                    tweet_text = f"{caption}\n({idx + 1}/{len(media_batches)})"
                else:
                    tweet_text = caption
                
                tweet_id = self.twitter_api.post_tweet(
                    text=tweet_text,
                    media_ids=media_ids,
                    reply_to_id=last_tweet_id,
                )
                
                if not tweet_id:
                    logger.error(f"Failed to post tweet for batch {idx + 1} of story {story_id}")
                    break
                
                tweet_ids.append(tweet_id)
                last_tweet_id = tweet_id
                logger.info(f"Posted tweet {idx + 1}/{len(media_batches)} for story {story_id}")
            
            if not tweet_ids:
                logger.error(f"Failed to post any tweets for story {story_id}")
                return False

            # Update archive
            self.archive_manager.update_story_tweets(username, story_id, tweet_ids)
            self.archive_manager.set_last_tweet_id(username, tweet_ids[-1])
            self.archive_manager.update_story_local_paths(username, story_id, None)

            # Cleanup all media files
            for media_path in media_paths:
                self.media_manager.cleanup_media(media_path)

            logger.info(f"Successfully posted story {story_id} for {username} with {len(tweet_ids)} tweet(s)")
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

    def archive_only(self) -> int:
        """Archive all available stories but DO NOT post them (for testing/debugging)."""
        total_processed = 0
        logger.info("Starting archive-only mode (no posting)")
        for username in self.config.INSTAGRAM_USERNAMES:
            total_processed += self.archive_all_stories_for_user(username)
        logger.info(f"Archive-only completed: {total_processed} stories archived")
        return total_processed

    def post_pending_stories(self) -> int:
        """Post all pending stories that were taken before the start of today (next day posting)."""
        total_posted = 0
        
        # Calculate the start of today in GMT+7
        now = datetime.now(timezone(timedelta(hours=7)))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Checking for pending stories taken before {today_start} (current time: {now})")

        for username in self.config.INSTAGRAM_USERNAMES:
            username = username.strip().lstrip('@')
            stats = self.archive_manager.get_statistics(username)
            stories = stats.get('stories', [])
            
            # Filter pending stories (not posted yet - no tweet_ids)
            pending = [s for s in stories if not s.get('tweet_ids')]
            
            if not pending:
                logger.info(f"No pending stories for {username}")
                continue
                
            # Sort by taken_at timestamp (oldest first)
            pending.sort(key=lambda x: int(x.get('taken_at', 0)))
            
            # Filter stories taken before today started
            stories_to_post = []
            for story in pending:
                taken_at = int(story.get('taken_at', 0))
                taken_at_dt = datetime.fromtimestamp(taken_at, tz=timezone(timedelta(hours=7)))
                
                if taken_at_dt < today_start:
                    stories_to_post.append(story)
                    logger.info(f"Story {story.get('story_id')} for {username} qualifies for posting (taken at {taken_at_dt})")
                else:
                    logger.info(f"Story {story.get('story_id')} for {username} is from today ({taken_at_dt}), skipping")
            
            if not stories_to_post:
                logger.info(f"No stories qualify for posting for {username}")
                continue
                
            logger.info(f"Posting {len(stories_to_post)} stories for {username}")
            
            # Post each qualifying story
            for story in stories_to_post:
                story_id = story.get('story_id')
                logger.info(f"Posting story {story_id} for {username}")
                if self.post_story(username, story_id):
                    total_posted += 1
                else:
                    logger.error(f"Failed to post story {story_id} for {username}")

        self.media_manager.cleanup_old_media()
        logger.info(f"Total stories posted: {total_posted}")
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
