import requests
import json
import logging
from typing import Any, Dict, List, Optional
from config import Config

logger = logging.getLogger(__name__)


class InstagramAPI:
    def __init__(self, config: Config, discord_notifier=None):
        self.config = config
        self.discord = discord_notifier
        self.base_url = "https://instagram120.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-key': config.RAPIDAPI_KEY,
            'x-rapidapi-host': config.RAPIDAPI_HOST,
            'Content-Type': 'application/json'
        }
    
    def _parse_story_items(self, payload: Optional[Any]) -> List[Dict]:
        if payload is None:
            return []
        
        if isinstance(payload, list):
            items: List[Dict] = []
            for entry in payload:
                if isinstance(entry, dict):
                    if any(key in entry for key in ('pk', 'id', 'image_versions2', 'video_versions')):
                        items.append(entry)
                    else:
                        items.extend(self._parse_story_items(entry))
            return items
        
        if isinstance(payload, dict):
            # Check for common response structures
            if 'result' in payload:
                result = payload.get('result')
                logger.debug(f"Found 'result' key with {len(result) if isinstance(result, list) else type(result)} items")
                return self._parse_story_items(result)
            
            # Check for pagination or nested structures
            aggregated: List[Dict] = []
            for key in ('items', 'stories', 'reels_media', 'tray', 'media', 'data', 'story_items'):
                if key in payload:
                    value = payload.get(key)
                    logger.debug(f"Found '{key}' key with {len(value) if isinstance(value, list) else type(value)} items")
                    aggregated.extend(self._parse_story_items(value))
            if aggregated:
                return aggregated
            
            # Check if this payload itself is a story
            if any(key in payload for key in ('pk', 'id', 'image_versions2', 'video_versions')):
                return [payload]
        
        logger.warning(f"Unable to parse story items from payload: {type(payload)}")
        return []
    
    def get_user_stories(self, username: str) -> Optional[List[Dict]]:
        """
        Fetch all active stories for a given Instagram username.
        """
        try:
            logger.info(f"Fetching stories for user: {username}")
            
            stories_url = f"{self.base_url}/api/instagram/stories"
            payload = {"username": username}
            
            response = requests.post(
                stories_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            story_data = response.json()
            logger.info(f"Stories response keys: {list(story_data.keys()) if isinstance(story_data, dict) else type(story_data)}")
            logger.debug(f"Stories response: {json.dumps(story_data, indent=2)[:1000]}")
            
            stories = self._parse_story_items(story_data)
            logger.info(f"Found {len(stories)} active stories for {username}")
            
            # Notify Discord about successful fetch
            if self.discord:
                self.discord.notify_instagram_fetch_success(username, len(stories))
            
            # Debug: Log details about each story found
            for i, story in enumerate(stories):
                story_id = story.get('pk') or story.get('id')
                taken_at = story.get('taken_at', 'unknown')
                logger.info(f"Story {i+1}: ID={story_id}, taken_at={taken_at}")
            
            return stories
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching user stories: {e}"
            logger.error(error_msg)
            
            # Notify Discord about Instagram API failure
            if self.discord:
                response_text = None
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        response_text = e.response.text[:1000]
                    except:
                        response_text = str(e.response)[:1000]
                
                self.discord.notify_instagram_fetch_error(
                    username=username,
                    error=str(e),
                    response_data=response_text
                )
            
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
        
        results = self._parse_story_items(story_data)
        if not results:
            logger.warning("No result in story data")
            return media_list
        
        for item in results:
            if not isinstance(item, dict):
                continue
            
            story_id = item.get('pk') or item.get('id')
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
