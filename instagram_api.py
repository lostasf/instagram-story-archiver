import requests
import json
import logging
from typing import Dict, List, Optional
from config import Config

logger = logging.getLogger(__name__)


class InstagramAPI:
    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://instagram120.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-key': config.RAPIDAPI_KEY,
            'x-rapidapi-host': config.RAPIDAPI_HOST,
            'Content-Type': 'application/json'
        }
    
    def get_user_stories(self, username: str) -> Optional[Dict]:
        """
        Fetch stories for a given Instagram username using user search.
        """
        try:
            logger.info(f"Fetching stories for user: {username}")
            
            # First, try to get user info to verify the username exists
            user_url = f"{self.base_url}/api/instagram/user"
            user_payload = {"username": username}
            
            response = requests.post(
                user_url,
                json=user_payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            user_data = response.json()
            logger.debug(f"User data response: {json.dumps(user_data, indent=2)[:500]}")
            
            return user_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching user stories: {e}")
            return None
    
    def get_story_by_id(self, username: str, story_id: str) -> Optional[Dict]:
        """
        Fetch a specific story by ID from a user.
        """
        try:
            logger.info(f"Fetching story {story_id} for user: {username}")
            
            story_url = f"{self.base_url}/api/instagram/story"
            payload = {
                "username": username,
                "storyId": story_id
            }
            
            response = requests.post(
                story_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            story_data = response.json()
            return story_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching story: {e}")
            return None
    
    def extract_media_urls(self, story_data: Dict) -> List[Dict]:
        """
        Extract media URLs from story data.
        Returns list of dicts with 'url', 'type', and 'story_id'
        """
        media_list = []
        
        if not story_data or 'result' not in story_data:
            logger.warning("No result in story data")
            return media_list
        
        results = story_data.get('result', [])
        if isinstance(results, dict):
            results = [results]
        
        for item in results:
            if not isinstance(item, dict):
                continue
            
            story_id = item.get('pk')
            media_type = 'image'
            url = None
            
            # Check for video
            if 'video_versions' in item:
                media_type = 'video'
                video_versions = item.get('video_versions', [])
                if video_versions:
                    url = video_versions[0].get('url')
            
            # Check for image
            elif 'image_versions2' in item:
                media_type = 'image'
                candidates = item.get('image_versions2', {}).get('candidates', [])
                if candidates:
                    # Get the highest quality version (first in list is typically highest)
                    url = candidates[0].get('url_downloadable') or candidates[0].get('url')
            
            if url:
                media_list.append({
                    'url': url,
                    'type': media_type,
                    'story_id': story_id,
                    'timestamp': item.get('taken_at')
                })
        
        logger.info(f"Extracted {len(media_list)} media items from story")
        return media_list
