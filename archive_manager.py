import json
import logging
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ArchiveManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.data = self._load_archive()
    
    def _load_archive(self) -> Dict:
        """Load archive database from file."""
        try:
            if Path(self.db_path).exists():
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded archive with {len(data.get('archived_stories', []))} stories")
                    return data
        except Exception as e:
            logger.error(f"Error loading archive: {e}")
        
        return {
            'archived_stories': [], 
            'last_check': None,
            'anchor_tweet_id': None,
            'last_tweet_id': None
        }
    
    def _save_archive(self) -> bool:
        """Save archive database to file."""
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.info(f"Saved archive with {len(self.data['archived_stories'])} stories")
            return True
        except Exception as e:
            logger.error(f"Error saving archive: {e}")
            return False
    
    def get_archived_story_ids(self) -> Set[str]:
        """Get set of all archived story IDs."""
        return set(s.get('story_id') for s in self.data.get('archived_stories', []))
    
    def add_story(self, story_id: str, story_data: Dict) -> bool:
        """Add a story to the archive."""
        try:
            if story_id in self.get_archived_story_ids():
                logger.info(f"Story {story_id} already archived")
                return False
            
            entry = {
                'story_id': story_id,
                'archived_at': datetime.now().isoformat(),
                'media_count': story_data.get('media_count', 0),
                'tweet_ids': story_data.get('tweet_ids', []),
                'media_urls': story_data.get('media_urls', [])
            }
            
            self.data['archived_stories'].append(entry)
            self.data['last_check'] = datetime.now().isoformat()
            
            logger.info(f"Added story {story_id} to archive")
            return self._save_archive()
            
        except Exception as e:
            logger.error(f"Error adding story to archive: {e}")
            return False
    
    def update_story_tweets(self, story_id: str, tweet_ids: list) -> bool:
        """Update tweet IDs for an archived story."""
        try:
            for entry in self.data.get('archived_stories', []):
                if entry.get('story_id') == story_id:
                    entry['tweet_ids'] = tweet_ids
                    logger.info(f"Updated story {story_id} with tweet IDs")
                    return self._save_archive()
            
            logger.warning(f"Story {story_id} not found in archive")
            return False
            
        except Exception as e:
            logger.error(f"Error updating story tweets: {e}")
            return False
    
    def get_anchor_tweet_id(self) -> Optional[str]:
        """Get the anchor tweet ID."""
        return self.data.get('anchor_tweet_id')
    
    def set_anchor_tweet_id(self, tweet_id: str) -> bool:
        """Set the anchor tweet ID."""
        try:
            self.data['anchor_tweet_id'] = tweet_id
            logger.info(f"Set anchor tweet ID: {tweet_id}")
            return self._save_archive()
        except Exception as e:
            logger.error(f"Error setting anchor tweet ID: {e}")
            return False
    
    def get_last_tweet_id(self) -> Optional[str]:
        """Get the last tweet ID in the thread."""
        return self.data.get('last_tweet_id')
    
    def set_last_tweet_id(self, tweet_id: str) -> bool:
        """Set the last tweet ID in the thread."""
        try:
            self.data['last_tweet_id'] = tweet_id
            logger.info(f"Set last tweet ID: {tweet_id}")
            return self._save_archive()
        except Exception as e:
            logger.error(f"Error setting last tweet ID: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get archive statistics."""
        stories = self.data.get('archived_stories', [])
        total_stories = len(stories)
        total_media = sum(s.get('media_count', 0) for s in stories)
        
        return {
            'total_stories': total_stories,
            'total_media': total_media,
            'last_check': self.data.get('last_check'),
            'stories': stories,
            'anchor_tweet_id': self.data.get('anchor_tweet_id'),
            'last_tweet_id': self.data.get('last_tweet_id')
        }
