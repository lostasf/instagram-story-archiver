import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


def _parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(',') if part.strip()]


class Config:
    def __init__(self):
        self.RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
        self.RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'instagram120.p.rapidapi.com')

        self.TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
        self.TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
        self.TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
        self.TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
        self.TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

        instagram_username_raw = os.getenv('INSTAGRAM_USERNAME') or 'jkt48.gendis'
        instagram_usernames_raw = os.getenv('INSTAGRAM_USERNAMES')

        parsed_from_instagram_username = [u.strip().lstrip('@') for u in _parse_csv(instagram_username_raw)]
        parsed_from_instagram_usernames = [u.strip().lstrip('@') for u in _parse_csv(instagram_usernames_raw)]

        # Priority:
        # 1) INSTAGRAM_USERNAMES (multi-account)
        # 2) INSTAGRAM_USERNAME (supports single username OR comma-separated list for backward compatibility)
        self.INSTAGRAM_USERNAMES = parsed_from_instagram_usernames or parsed_from_instagram_username

        # Backward compatibility: keep INSTAGRAM_USERNAME pointing to the primary account
        self.INSTAGRAM_USERNAME = self.INSTAGRAM_USERNAMES[0]

        instagram_template_names_raw = os.getenv('INSTAGRAM_TEMPLATE_NAMES')
        self.INSTAGRAM_TEMPLATE_NAMES = _parse_csv(instagram_template_names_raw)

        self.USERNAME_TO_TEMPLATE_NAME = {}
        for i, username in enumerate(self.INSTAGRAM_USERNAMES):
            if i < len(self.INSTAGRAM_TEMPLATE_NAMES):
                self.USERNAME_TO_TEMPLATE_NAME[username] = self.INSTAGRAM_TEMPLATE_NAMES[i]

        self.ARCHIVE_DB_PATH = os.getenv('ARCHIVE_DB_PATH', './archive.json')
        self.MEDIA_CACHE_DIR = os.getenv('MEDIA_CACHE_DIR', './media_cache')

        self.TWITTER_THREAD_CONFIG = self._load_thread_config()

    def _load_thread_config(self) -> Dict[str, Dict[str, Any]]:
        raw = os.getenv('TWITTER_THREAD_CONFIG')
        if not raw:
            return {}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                "Invalid TWITTER_THREAD_CONFIG JSON. "
                "Expected something like: {\"jkt48.gendis\": {\"anchor_text\": \"...\"}}"
            ) from e

        if not isinstance(parsed, dict):
            raise ValueError("TWITTER_THREAD_CONFIG must be a JSON object mapping username -> config")

        normalized: Dict[str, Dict[str, Any]] = {}
        for username, config in parsed.items():
            if not isinstance(username, str):
                continue
            if not isinstance(config, dict):
                continue
            normalized[username.strip().lstrip('@')] = config

        return normalized

    def get_story_caption(self, instagram_username: str, taken_at_timestamp: int) -> str:
        """
        Get the customizable caption for a story tweet.
        
        TO UPDATE CAPTION TEMPLATES:
        Modify the return values in this method based on the username.
        The template follows the format:
        Instagram Story @Username
        DD/MM/YYYY
        
        #Hashtag
        """
        username = instagram_username.strip().lstrip('@')
        
        # Format date as DD/MM/YYYY in GMT+7
        from datetime import datetime, timedelta, timezone
        utc_plus_7 = timezone(timedelta(hours=7))
        dt = datetime.fromtimestamp(taken_at_timestamp, tz=utc_plus_7)
        date_str = dt.strftime("%d/%m/%Y")

        # Specific requirements for Gendis and Lana
        if 'gendis' in username.lower():
            return f"Instagram Story @Gendis_JKT48\n{date_str}\n\n#Mantrajiva"
        
        if 'lana' in username.lower():
            # Matches 'lana' or 'jkt48.lana.a'
            return f"Instagram Story Lana\n{date_str}"

        # Default fallback
        return f"Instagram Story {username}\n{date_str}"

    def get_anchor_text(self, instagram_username: str) -> str:
        username = instagram_username.strip().lstrip('@')

        configured = self.TWITTER_THREAD_CONFIG.get(username, {})
        anchor_text = configured.get('anchor_text')
        if isinstance(anchor_text, str) and anchor_text.strip():
            return anchor_text.strip()

        # Check for template name
        template_name = configured.get('template_name')
        if not template_name:
            template_name = self.USERNAME_TO_TEMPLATE_NAME.get(username)

        if template_name:
            if 'jkt48' in username.lower():
                return f"{template_name} JKT48 Instagram Story"
            return f"{template_name} Instagram Story"

        # Sensible defaults
        if username == 'jkt48.gendis':
            return 'Gendis JKT48 Instagram Story'
        if username == 'jkt48.lana.a':
            return 'Lana JKT48 Instagram Story'

        return f"{username} Instagram Story"

    def validate(self):
        required = [
            'RAPIDAPI_KEY',
            'TWITTER_API_KEY',
            'TWITTER_API_SECRET',
            'TWITTER_ACCESS_TOKEN',
            'TWITTER_ACCESS_SECRET',
            'TWITTER_BEARER_TOKEN',
        ]
        missing = [key for key in required if not getattr(self, key)]
        if missing:
            raise ValueError(f"Missing configuration: {', '.join(missing)}")

        if not self.INSTAGRAM_USERNAMES:
            raise ValueError('No Instagram usernames configured. Set INSTAGRAM_USERNAME or INSTAGRAM_USERNAMES.')
