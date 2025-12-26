import logging
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

    def process_story(self, username: str, story_id: str, story_payload: Optional[Dict] = None) -> bool:
        """Process a single story: download media and post to Twitter thread."""
        username = username.strip().lstrip('@')

        try:
            story_id = str(story_id)
            logger.info(f"=== Starting process_story for {story_id} from {username} ===")

            # Check if already archived (per account)
            archived_ids = self.archive_manager.get_archived_story_ids(username)
            if story_id in archived_ids:
                logger.info(f"Story {story_id} already archived for {username}, skipping")
                return False

            # Ensure anchor tweet exists for this account
            anchor_id = self._ensure_anchor_tweet(username)
            if not anchor_id:
                logger.error("Cannot proceed without anchor tweet")
                return False

            # Fetch story from Instagram when payload is not provided
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

            logger.info(f"Story {story_id} has {len(media_list)} media items")

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

            datetime_text = self._format_story_datetime(taken_at)

            last_tweet_id = self.archive_manager.get_last_tweet_id(username) or anchor_id

            media_id = self.twitter_api.upload_media(media_path)
            if not media_id:
                logger.error(f"Failed to upload media for story {story_id}")
                self.media_manager.cleanup_media(media_path)
                return False

            tweet_id = self.twitter_api.post_tweet(
                text=datetime_text,
                media_ids=[media_id],
                reply_to_id=last_tweet_id,
            )

            if not tweet_id:
                logger.error(f"Failed to post tweet for story {story_id}")
                self.media_manager.cleanup_media(media_path)
                return False

            self.archive_manager.set_last_tweet_id(username, tweet_id)

            archive_data = {
                'media_count': len(media_list),
                'media_urls': [m['url'] for m in media_list],
                'tweet_ids': [tweet_id],
                'taken_at': taken_at,
            }
            self.archive_manager.add_story(username, story_id, archive_data)

            self.media_manager.cleanup_media(media_path)

            logger.info(f"Successfully archived story {story_id} for {username}")
            logger.info(f"=== Completed process_story for {story_id} ===")
            return True

        except Exception as e:
            logger.error(
                f"Error processing story {story_id} for {username}: {e}",
                exc_info=True,
            )
            logger.info(f"=== Failed process_story for {story_id} ===")
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

                success = self.process_story(username, story_id_str, story_payload=story)
                logger.info(f"Story {story_id_str} processing result for {username}: {success}")

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
