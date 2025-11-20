#!/usr/bin/env python3
"""
Test script to verify configuration and API connectivity.
Run this before starting the main application.
"""

import sys
import os
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
        interval = getattr(config, 'CHECK_INTERVAL_HOURS', None)
        if interval is not None:
            logger.info(f"  - Check Interval: {interval} hour(s)")
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
        
        # Try to fetch active stories
        stories = api.get_user_stories(config.INSTAGRAM_USERNAME)
        if stories is None:
            logger.error("✗ Failed to fetch stories from Instagram API")
            return False
        
        story_count = len(stories)
        logger.info("✓ Successfully connected to Instagram API")
        logger.info(f"  Active stories found: {story_count}")
        if story_count == 0:
            logger.warning("⚠ No active stories available right now (this is normal if the user has none)")
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
            
            # Test media upload permissions (if we have a test file)
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
                logger.info("  Create a test image file to verify media upload permissions")
            
            return True
        else:
            logger.error("✗ Failed to authenticate with Twitter API")
            return False
    except Exception as e:
        error_msg = str(e).lower()
        if "oauth1 app permissions" in error_msg or "403" in error_msg:
            logger.error("✗ Twitter OAuth 1.0a permission error detected")
            logger.error("  Please see TWITTER_OAUTH_FIX.md for detailed instructions")
            logger.error("  Summary: Update app permissions to 'Read and Write' and regenerate tokens")
        else:
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
