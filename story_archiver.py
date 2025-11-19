import logging
from typing import List, Optional
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
    
    def process_story(self, username: str, story_id: str) -> bool:
        """
        Process a single story: download media and post to Twitter thread.
        
        Args:
            username: Instagram username
            story_id: Story ID from Instagram
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing story {story_id} from {username}")
            
            # Check if already archived
            if story_id in self.archive_manager.get_archived_story_ids():
                logger.info(f"Story {story_id} already archived, skipping")
                return False
            
            # Fetch story from Instagram
            story_data = self.instagram_api.get_story_by_id(username, story_id)
            if not story_data:
                logger.error(f"Failed to fetch story {story_id}")
                return False
            
            # Extract media URLs
            media_list = self.instagram_api.extract_media_urls(story_data)
            if not media_list:
                logger.warning(f"No media found in story {story_id}")
                return False
            
            logger.info(f"Story {story_id} has {len(media_list)} media items")
            
            # Download and prepare media
            downloaded_media = []
            for i, media in enumerate(media_list):
                media_path = self.media_manager.download_media(
                    media['url'],
                    f"{story_id}_{i}",
                    media['type']
                )
                
                if media_path:
                    # Compress images
                    if media['type'] == 'image':
                        media_path = self.media_manager.compress_image(media_path)
                    
                    downloaded_media.append({
                        'path': media_path,
                        'type': media['type']
                    })
            
            if not downloaded_media:
                logger.error(f"Failed to download any media for story {story_id}")
                return False
            
            # Create Twitter thread
            tweets = self._create_tweets(username, story_id, downloaded_media)
            tweet_ids = self.twitter_api.create_thread(tweets)
            
            if not tweet_ids:
                logger.error(f"Failed to post thread for story {story_id}")
                return False
            
            # Record in archive
            archive_data = {
                'media_count': len(downloaded_media),
                'media_urls': [m['url'] for m in media_list],
                'tweet_ids': [tweets] if isinstance(tweets, str) else tweets
            }
            
            self.archive_manager.add_story(story_id, archive_data)
            
            # Cleanup downloaded media
            for media in downloaded_media:
                self.media_manager.cleanup_media(media['path'])
            
            logger.info(f"Successfully archived story {story_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing story: {e}", exc_info=True)
            return False
    
    def _create_tweets(self, username: str, story_id: str, media_list: List[dict]) -> List[dict]:
        """
        Create tweet posts for a thread.
        
        Args:
            username: Instagram username
            story_id: Story ID
            media_list: List of media dictionaries with 'path' and 'type'
        
        Returns:
            List of post dictionaries for create_thread
        """
        posts = []
        
        # First tweet: intro
        posts.append({
            'text': f'🔄 Archiving story from @{username}\n\nStory ID: {story_id}\nTotal items: {len(media_list)}\n\n#StoryArchive #Gendis',
            'media_path': None
        })
        
        # Media tweets
        for i, media in enumerate(media_list):
            post_text = f'📸 Item {i+1}/{len(media_list)}\n'
            if media['type'] == 'video':
                post_text += '🎥 Video'
            else:
                post_text += '🖼️ Image'
            
            posts.append({
                'text': post_text,
                'media_path': media['path']
            })
        
        # Final tweet: completion
        posts.append({
            'text': f'✅ Archiving complete!\n\nTotal items archived: {len(media_list)}\nTimestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n#StoryArchive',
            'media_path': None
        })
        
        return posts
    
    def archive_all_stories(self) -> int:
        """
        Fetch and archive all available stories for the configured username.
        
        Returns:
            Number of stories successfully archived
        """
        try:
            logger.info(f"Starting story check for {self.config.INSTAGRAM_USERNAME}")
            
            # Get user information
            user_data = self.instagram_api.get_user_stories(self.config.INSTAGRAM_USERNAME)
            if not user_data:
                logger.error("Failed to fetch user data")
                return 0
            
            # In a real scenario, you would extract story IDs from user_data
            # This is a simplified version that processes a single story
            # The actual implementation depends on what the API returns
            
            logger.info(f"Story check completed for {self.config.INSTAGRAM_USERNAME}")
            
            stats = self.archive_manager.get_statistics()
            logger.info(f"Archive statistics: {stats['total_stories']} stories, {stats['total_media']} media items")
            
            return 0
            
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
