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

    def get_anchor_text(self, instagram_username: str) -> str:
        username = instagram_username.strip().lstrip('@')

        configured = self.TWITTER_THREAD_CONFIG.get(username, {})
        anchor_text = configured.get('anchor_text')
        if isinstance(anchor_text, str) and anchor_text.strip():
            return anchor_text.strip()

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
