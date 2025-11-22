import logging
from typing import Dict, List, Optional
from datetime import datetime

from config import Config
from instagram_api import InstagramAPI
from twitter_api import TwitterAPI
from media_manager import MediaManager
from archive_manager import ArchiveManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StoryArchiver:
    def __init__(self, config: Config):
        self.config = config
        self.instagram_api = InstagramAPI(config)
        self.twitter_api = TwitterAPI(config)
        self.media_manager = MediaManager(config.MEDIA_CACHE_DIR)
        self.archive_manager = ArchiveManager(config.ARCHIVE_DB_PATH)
    
    def _format_story_datetime(self, taken_at: int) -> str:
        """
        Format Unix timestamp to human-readable datetime.
        Example: "Thursday, 02 November 2025 14:48"
        """
        dt = datetime.fromtimestamp(taken_at)
        return dt.strftime("%A, %d %B %Y %H:%M")
    
    def _ensure_anchor_tweet(self) -> Optional[str]:
        """
        Ensure the anchor tweet exists. Create it if it doesn't.
        Returns the anchor tweet ID.
        """
        anchor_id = self.archive_manager.get_anchor_tweet_id()
        
        if anchor_id:
            logger.info(f"Using existing anchor tweet: {anchor_id}")
            return anchor_id
        
        # Create anchor tweet
        logger.info("Creating anchor tweet...")
        anchor_text = "Gendis JKT48 Instagram Story"
        anchor_id = self.twitter_api.post_tweet(anchor_text)
        
        if anchor_id:
            self.archive_manager.set_anchor_tweet_id(anchor_id)
            self.archive_manager.set_last_tweet_id(anchor_id)
            logger.info(f"Anchor tweet created: {anchor_id}")
            return anchor_id
        else:
            logger.error("Failed to create anchor tweet")
            return None
    
    def process_story(self, username: str, story_id: str, story_payload: Optional[Dict] = None) -> bool:
        """
        Process a single story: download media and post to Twitter thread.
        
        Args:
            username: Instagram username
            story_id: Story ID from Instagram
            story_payload: Optional pre-fetched story data to avoid extra API calls
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"=== Starting process_story for {story_id} from {username} ===")
            
            # Check if already archived
            archived_ids = self.archive_manager.get_archived_story_ids()
            logger.info(f"Current archived IDs: {list(archived_ids)}")
            if story_id in archived_ids:
                logger.info(f"Story {story_id} already archived, skipping")
                return False
            
            # Ensure anchor tweet exists
            anchor_id = self._ensure_anchor_tweet()
            if not anchor_id:
                logger.error("Cannot proceed without anchor tweet")
                return False
            
            # Fetch story from Instagram when payload is not provided
            story_data = story_payload if story_payload is not None else self.instagram_api.get_story_by_id(username, story_id)
            if not story_data:
                logger.error(f"Failed to fetch story {story_id}")
                return False
            
            # Extract taken_at timestamp
            taken_at = story_data.get('taken_at', 0)
            
            # Extract media URLs
            media_list = self.instagram_api.extract_media_urls(story_data)
            if not media_list:
                logger.warning(f"No media found in story {story_id}")
                return False
            
            logger.info(f"Story {story_id} has {len(media_list)} media items")
            
            # Download and prepare media (only first media item per story)
            media = media_list[0]
            media_path = self.media_manager.download_media(
                media['url'],
                f"{story_id}_0",
                media['type']
            )
            
            if not media_path:
                logger.error(f"Failed to download media for story {story_id}")
                return False
            
            # Compress images
            if media['type'] == 'image':
                media_path = self.media_manager.compress_image(media_path)
            
            # Format datetime for tweet
            datetime_text = self._format_story_datetime(taken_at)
            
            # Get the last tweet ID to reply to
            last_tweet_id = self.archive_manager.get_last_tweet_id()
            if not last_tweet_id:
                last_tweet_id = anchor_id
            
            # Upload media
            media_id = self.twitter_api.upload_media(media_path)
            if not media_id:
                logger.error(f"Failed to upload media for story {story_id}")
                self.media_manager.cleanup_media(media_path)
                return False
            
            # Post tweet as reply to last tweet
            tweet_id = self.twitter_api.post_tweet(
                text=datetime_text,
                media_ids=[media_id],
                reply_to_id=last_tweet_id
            )
            
            if not tweet_id:
                logger.error(f"Failed to post tweet for story {story_id}")
                self.media_manager.cleanup_media(media_path)
                return False
            
            # Update last tweet ID
            self.archive_manager.set_last_tweet_id(tweet_id)
            
            # Record in archive
            archive_data = {
                'media_count': len(media_list),
                'media_urls': [m['url'] for m in media_list],
                'tweet_ids': [tweet_id],
                'taken_at': taken_at
            }
            
            self.archive_manager.add_story(story_id, archive_data)
            
            # Cleanup downloaded media
            self.media_manager.cleanup_media(media_path)
            
            logger.info(f"Successfully archived story {story_id}")
            logger.info(f"=== Completed process_story for {story_id} ===")
            return True
            
        except Exception as e:
            logger.error(f"Error processing story {story_id}: {e}", exc_info=True)
            logger.info(f"=== Failed process_story for {story_id} ===")
            return False
    
    def archive_all_stories(self) -> int:
        """
        Fetch and archive all available stories for the configured username.
        
        Returns:
            Number of stories successfully archived
        """
        try:
            username = self.config.INSTAGRAM_USERNAME
            logger.info(f"Starting story check for {username}")
            
            stories = self.instagram_api.get_user_stories(username)
            if stories is None:
                logger.error("Failed to fetch stories from Instagram API")
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
            logger.info(f"Found {len(story_items)} stories to evaluate")
            
            # Validate story structure
            for i, story in enumerate(story_items):
                story_id = story.get('pk') or story.get('id')
                if not story_id:
                    logger.warning(f"Story {i} missing both 'pk' and 'id' keys: {list(story.keys())}")
                if 'image_versions2' not in story and 'video_versions' not in story:
                    logger.warning(f"Story {story_id} has no media: {list(story.keys())}")
            
            # Debug: Log all story IDs found
            story_ids = [str(s.get('pk') or s.get('id')) for s in story_items if s.get('pk') or s.get('id')]
            logger.info(f"Story IDs found: {story_ids}")
            
            archived_ids = {str(sid) for sid in self.archive_manager.get_archived_story_ids() if sid is not None}
            logger.info(f"Already archived story IDs: {list(archived_ids)}")
            processed_count = 0
            
            if not story_items:
                logger.info("No active stories available at this time")
            
            for i, story in enumerate(story_items):
                story_id = story.get('pk') or story.get('id')
                if not story_id:
                    logger.debug(f"Skipping story {i} without an ID")
                    continue
                
                story_id = str(story_id)
                logger.info(f"Processing story {i+1}/{len(story_items)}: {story_id}")
                
                if story_id in archived_ids:
                    logger.info(f"Story {story_id} already archived, skipping")
                    continue
                
                logger.info(f"Attempting to process story {story_id}")
                success = self.process_story(username, story_id, story_payload=story)
                logger.info(f"Story {story_id} processing result: {success}")
                
                if success:
                    processed_count += 1
                    archived_ids.add(story_id)
                    logger.info(f"Successfully processed story {story_id}. Total processed: {processed_count}")
                else:
                    logger.warning(f"Failed to process story {story_id}")
            
            logger.info(f"Story check completed for {username}")
            logger.info(f"New stories archived: {processed_count}")
            
            stats = self.archive_manager.get_statistics()
            logger.info(f"Archive statistics: {stats['total_stories']} stories, {stats['total_media']} media items")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error archiving stories: {e}", exc_info=True)
            return 0
    
    def print_status(self) -> None:
        """Print current archive status."""
        stats = self.archive_manager.get_statistics()
        logger.info("="*50)
        logger.info("ARCHIVE STATUS")
        logger.info(f"Total Stories: {stats['total_stories']}")
        logger.info(f"Total Media Items: {stats['total_media']}")
        logger.info(f"Last Check: {stats['last_check']}")
        logger.info("="*50)
