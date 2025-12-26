#!/usr/bin/env python3
"""Test script to verify configuration and API connectivity.

Run this before starting the main application.
"""

import os
import sys
import logging

from config import Config
from instagram_api import InstagramAPI
from twitter_api import TwitterAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_config() -> Config:
    """Test configuration loading."""
    logger.info("Testing configuration...")
    config = Config()
    config.validate()

    logger.info("✓ Configuration loaded successfully")
    logger.info(f"  - Instagram Usernames: {', '.join(config.INSTAGRAM_USERNAMES)}")
    logger.info(f"  - Primary Instagram Username: {config.INSTAGRAM_USERNAME}")

    template_names = [f"{u}: {config.USERNAME_TO_TEMPLATE_NAME.get(u, 'None')}" for u in config.INSTAGRAM_USERNAMES]
    logger.info(f"  - Template Names: {', '.join(template_names)}")

    logger.info(f"  - Archive DB: {config.ARCHIVE_DB_PATH}")
    logger.info(f"  - Media Cache: {config.MEDIA_CACHE_DIR}")
    return config


def test_instagram_api(config: Config) -> bool:
    """Test Instagram API connectivity."""
    logger.info("\nTesting Instagram API...")

    try:
        api = InstagramAPI(config)
        logger.info("✓ Instagram API initialized")

        all_ok = True
        for username in config.INSTAGRAM_USERNAMES:
            stories = api.get_user_stories(username)
            if stories is None:
                logger.error(f"✗ Failed to fetch stories from Instagram API for {username}")
                all_ok = False
                continue

            story_count = len(stories)
            logger.info(f"✓ Successfully connected to Instagram API for {username}")
            logger.info(f"  Active stories found: {story_count}")
            if story_count == 0:
                logger.warning("⚠ No active stories available right now (this is normal if the user has none)")

        return all_ok

    except Exception as e:
        logger.error(f"✗ Instagram API error: {e}")
        return False


def test_twitter_api(config: Config) -> bool:
    """Test Twitter API connectivity."""
    logger.info("\nTesting Twitter API...")

    try:
        api = TwitterAPI(config)
        logger.info("✓ Twitter API initialized")

        user = api.client.get_me()
        if not user or not user.data:
            logger.error("✗ Failed to authenticate with Twitter API")
            return False

        logger.info("✓ Successfully authenticated to Twitter API")
        logger.info(f"  - Username: @{user.data.username}")

        test_media_path = "./test_media.jpg"
        if os.path.exists(test_media_path):
            logger.info("Testing media upload permissions...")
            media_id = api.upload_media(test_media_path)
            if media_id:
                logger.info("✓ Media upload permissions verified")
            else:
                logger.warning("⚠ Media upload failed - check OAuth 1.0a permissions")
                logger.warning("  See TWITTER_OAUTH_FIX.md for instructions")
        else:
            logger.info("  (Skipping media upload test - no test file found)")

        return True

    except Exception as e:
        error_msg = str(e).lower()
        if "oauth1 app permissions" in error_msg or "403" in error_msg:
            logger.error("✗ Twitter OAuth 1.0a permission error detected")
            logger.error("  Please see TWITTER_OAUTH_FIX.md for detailed instructions")
            logger.error("  Summary: Update app permissions to 'Read and Write' and regenerate tokens")
        else:
            logger.error(f"✗ Twitter API error: {e}")
        return False


def main() -> bool:
    logger.info("=" * 60)
    logger.info("Story Archiver - Setup Test")
    logger.info("=" * 60)

    try:
        config = test_config()
    except ValueError as e:
        logger.error(f"\n✗ Configuration test failed: {e}")
        return False

    instagram_ok = test_instagram_api(config)
    twitter_ok = test_twitter_api(config)

    logger.info("\n" + "=" * 60)
    if instagram_ok and twitter_ok:
        logger.info("✓ All tests passed! Ready to start archiving.")
        logger.info("=" * 60)
        return True

    logger.warning("⚠ Some tests failed. Please check your configuration.")
    logger.info("=" * 60)
    return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
