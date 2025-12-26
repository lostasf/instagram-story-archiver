import json
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def _empty_account() -> Dict[str, Any]:
    return {
        'archived_stories': [],
        'last_check': None,
        'anchor_tweet_id': None,
        'last_tweet_id': None,
    }


class ArchiveManager:
    def __init__(self, db_path: str, default_instagram_username: Optional[str] = None):
        self.db_path = db_path
        self.default_instagram_username = (default_instagram_username or 'default').strip().lstrip('@')
        self.data = self._load_archive()

    def _load_archive(self) -> Dict[str, Any]:
        """Load archive database from file."""
        if not Path(self.db_path).exists():
            return {
                'schema_version': 2,
                'accounts': {},
            }

        try:
            with open(self.db_path, 'r') as f:
                raw = json.load(f)
        except Exception as e:
            logger.error(f"Error loading archive: {e}")
            return {
                'schema_version': 2,
                'accounts': {},
            }

        # New schema
        if isinstance(raw, dict) and isinstance(raw.get('accounts'), dict):
            data: Dict[str, Any] = {
                'schema_version': int(raw.get('schema_version') or 2),
                'accounts': raw.get('accounts') or {},
            }
            return self._normalize_data(data)

        # Legacy schema (single account)
        if isinstance(raw, dict) and 'archived_stories' in raw:
            migrated = {
                'schema_version': 2,
                'accounts': {
                    self.default_instagram_username: {
                        'archived_stories': raw.get('archived_stories') or [],
                        'last_check': raw.get('last_check'),
                        'anchor_tweet_id': raw.get('anchor_tweet_id'),
                        'last_tweet_id': raw.get('last_tweet_id'),
                    }
                },
            }
            logger.info(
                "Loaded legacy archive format. Migrating to multi-account format "
                f"under account '{self.default_instagram_username}'."
            )
            return self._normalize_data(migrated)

        # Unknown format
        logger.warning(f"Unknown archive.json format. Re-initializing archive: {type(raw)}")
        return {
            'schema_version': 2,
            'accounts': {},
        }

    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        accounts = data.get('accounts')
        if not isinstance(accounts, dict):
            accounts = {}

        normalized_accounts: Dict[str, Any] = {}
        for username, account in accounts.items():
            if not isinstance(username, str):
                continue
            if not isinstance(account, dict):
                continue

            merged = _empty_account()
            merged.update(account)

            stories = merged.get('archived_stories')
            if not isinstance(stories, list):
                merged['archived_stories'] = []

            normalized_accounts[username.strip().lstrip('@')] = merged

        return {
            'schema_version': 2,
            'accounts': normalized_accounts,
        }

    def _save_archive(self) -> bool:
        """Save archive database to file."""
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            total_stories = sum(
                len((acct or {}).get('archived_stories') or [])
                for acct in (self.data.get('accounts') or {}).values()
            )
            logger.info(f"Saved archive with {total_stories} stories")
            return True
        except Exception as e:
            logger.error(f"Error saving archive: {e}")
            return False

    def _account_key(self, instagram_username: Optional[str]) -> str:
        key = (instagram_username or self.default_instagram_username).strip().lstrip('@')
        return key

    def _get_account(self, instagram_username: Optional[str]) -> Dict[str, Any]:
        username = self._account_key(instagram_username)
        accounts = self.data.setdefault('accounts', {})
        if username not in accounts or not isinstance(accounts.get(username), dict):
            accounts[username] = _empty_account()
        else:
            merged = _empty_account()
            merged.update(deepcopy(accounts[username]))
            accounts[username] = merged
        return accounts[username]

    def get_archived_story_ids(self, instagram_username: Optional[str] = None) -> Set[str]:
        """Get set of all archived story IDs for a specific account."""
        account = self._get_account(instagram_username)
        ids: Set[str] = set()
        for entry in account.get('archived_stories', []):
            if not isinstance(entry, dict):
                continue
            story_id = entry.get('story_id')
            if story_id is None:
                continue
            ids.add(str(story_id))
        return ids

    def add_story(self, instagram_username: str, story_id: str, story_data: Dict[str, Any]) -> bool:
        """Add a story to the archive for a specific account."""
        try:
            account = self._get_account(instagram_username)
            story_id_str = str(story_id)

            if story_id_str in self.get_archived_story_ids(instagram_username):
                logger.info(f"Story {story_id_str} already archived for {instagram_username}")
                return False

            entry: Dict[str, Any] = {
                'story_id': story_id_str,
                'instagram_username': instagram_username,
                'archived_at': datetime.now().isoformat(),
                'media_count': story_data.get('media_count', 0),
                'tweet_ids': story_data.get('tweet_ids', []),
                'media_urls': story_data.get('media_urls', []),
                'taken_at': story_data.get('taken_at'),
            }

            account['archived_stories'].append(entry)
            account['last_check'] = datetime.now().isoformat()

            logger.info(f"Added story {story_id_str} to archive for {instagram_username}")
            return self._save_archive()

        except Exception as e:
            logger.error(f"Error adding story to archive: {e}")
            return False

    def update_story_tweets(self, instagram_username: str, story_id: str, tweet_ids: List[str]) -> bool:
        """Update tweet IDs for an archived story."""
        try:
            account = self._get_account(instagram_username)
            story_id_str = str(story_id)

            for entry in account.get('archived_stories', []):
                if not isinstance(entry, dict):
                    continue
                if str(entry.get('story_id')) == story_id_str:
                    entry['tweet_ids'] = tweet_ids
                    logger.info(f"Updated story {story_id_str} with tweet IDs")
                    return self._save_archive()

            logger.warning(f"Story {story_id_str} not found in archive for {instagram_username}")
            return False

        except Exception as e:
            logger.error(f"Error updating story tweets: {e}")
            return False

    def get_anchor_tweet_id(self, instagram_username: Optional[str] = None) -> Optional[str]:
        """Get the anchor tweet ID for the account."""
        account = self._get_account(instagram_username)
        value = account.get('anchor_tweet_id')
        return str(value) if value else None

    def set_anchor_tweet_id(self, instagram_username: str, tweet_id: str) -> bool:
        """Set the anchor tweet ID for the account."""
        try:
            account = self._get_account(instagram_username)
            account['anchor_tweet_id'] = str(tweet_id)
            logger.info(f"Set anchor tweet ID for {instagram_username}: {tweet_id}")
            return self._save_archive()
        except Exception as e:
            logger.error(f"Error setting anchor tweet ID: {e}")
            return False

    def get_last_tweet_id(self, instagram_username: Optional[str] = None) -> Optional[str]:
        """Get the last tweet ID in the thread for the account."""
        account = self._get_account(instagram_username)
        value = account.get('last_tweet_id')
        return str(value) if value else None

    def set_last_tweet_id(self, instagram_username: str, tweet_id: str) -> bool:
        """Set the last tweet ID in the thread for the account."""
        try:
            account = self._get_account(instagram_username)
            account['last_tweet_id'] = str(tweet_id)
            logger.info(f"Set last tweet ID for {instagram_username}: {tweet_id}")
            return self._save_archive()
        except Exception as e:
            logger.error(f"Error setting last tweet ID: {e}")
            return False

    def get_statistics(self, instagram_username: Optional[str] = None) -> Dict[str, Any]:
        """Get archive statistics for one or all accounts."""
        if instagram_username:
            account = self._get_account(instagram_username)
            stories = account.get('archived_stories', [])
            total_stories = len(stories)
            total_media = sum((s or {}).get('media_count', 0) for s in stories if isinstance(s, dict))

            return {
                'instagram_username': self._account_key(instagram_username),
                'total_stories': total_stories,
                'total_media': total_media,
                'last_check': account.get('last_check'),
                'stories': stories,
                'anchor_tweet_id': account.get('anchor_tweet_id'),
                'last_tweet_id': account.get('last_tweet_id'),
            }

        accounts = self.data.get('accounts', {})
        per_account: Dict[str, Any] = {}
        for username in sorted(accounts.keys()):
            per_account[username] = self.get_statistics(username)

        total_stories_all = sum(stats.get('total_stories', 0) for stats in per_account.values())
        total_media_all = sum(stats.get('total_media', 0) for stats in per_account.values())

        return {
            'schema_version': 2,
            'total_stories': total_stories_all,
            'total_media': total_media_all,
            'accounts': per_account,
        }
