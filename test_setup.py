#!/usr/bin/env python3
"""
Test script to verify configuration and API connectivity.
Run this before starting the main application.
"""

import sys
import logging
from config import Config
from instagram_api import InstagramAPI
from twitter_api import TwitterAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    try:
        config = Config()
        config.validate()
        logger.info("✓ Configuration loaded successfully")
        logger.info(f"  - Instagram Username: {config.INSTAGRAM_USERNAME}")
        logger.info(f"  - Check Interval: {config.CHECK_INTERVAL_HOURS} hour(s)")
        logger.info(f"  - Archive DB: {config.ARCHIVE_DB_PATH}")
        logger.info(f"  - Media Cache: {config.MEDIA_CACHE_DIR}")
        return config
    except ValueError as e:
        logger.error(f"✗ Configuration error: {e}")
        return None


def test_instagram_api(config):
    """Test Instagram API connectivity."""
    logger.info("\nTesting Instagram API...")
    try:
        api = InstagramAPI(config)
        logger.info("✓ Instagram API initialized")
        
        # Try to fetch user info
        user_data = api.get_user_stories(config.INSTAGRAM_USERNAME)
        if user_data:
            logger.info(f"✓ Successfully connected to Instagram API")
            logger.info(f"  Response keys: {list(user_data.keys())}")
            return True
        else:
            logger.warning("⚠ Instagram API returned no data (may need valid story ID)")
            return True
    except Exception as e:
        logger.error(f"✗ Instagram API error: {e}")
        return False


def test_twitter_api(config):
    """Test Twitter API connectivity."""
    logger.info("\nTesting Twitter API...")
    try:
        api = TwitterAPI(config)
        logger.info("✓ Twitter API initialized")
        
        # Test by getting authenticated user
        user = api.client.get_me()
        if user and user.data:
            logger.info(f"✓ Successfully authenticated to Twitter API")
            logger.info(f"  - Username: @{user.data.username}")
            return True
        else:
            logger.error("✗ Failed to authenticate with Twitter API")
            return False
    except Exception as e:
        logger.error(f"✗ Twitter API error: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Gendis Story Archiver - Setup Test")
    logger.info("=" * 60)
    
    # Test config
    config = test_config()
    if not config:
        logger.error("\n✗ Configuration test failed")
        return False
    
    # Test Instagram API
    instagram_ok = test_instagram_api(config)
    
    # Test Twitter API
    twitter_ok = test_twitter_api(config)
    
    # Summary
    logger.info("\n" + "=" * 60)
    if instagram_ok and twitter_ok:
        logger.info("✓ All tests passed! Ready to start archiving.")
        logger.info("=" * 60)
        return True
    else:
        logger.warning("⚠ Some tests failed. Please check your configuration.")
        logger.info("=" * 60)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
