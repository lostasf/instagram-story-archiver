#!/usr/bin/env python3
"""
Twitter OAuth 1.0a Permissions Diagnostic Tool
Helps diagnose and provide guidance for fixing OAuth 1.0a permission issues.
"""

import sys
import os
import logging
from config import Config
from twitter_api import TwitterAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def diagnose_oauth_permissions():
    """Diagnose Twitter OAuth 1.0a permissions."""
    logger.info("=" * 60)
    logger.info("Twitter OAuth 1.0a Permissions Diagnostic")
    logger.info("=" * 60)
    
    try:
        # Load config
        config = Config()
        config.validate()
        logger.info("✓ Configuration loaded successfully")
        
        # Initialize Twitter API
        api = TwitterAPI(config)
        logger.info("✓ Twitter API initialized")
        
        # Test OAuth 2.0 (get user info)
        logger.info("\n1. Testing OAuth 2.0 authentication...")
        try:
            user = api.client.get_me()
            if user and user.data:
                logger.info(f"✓ OAuth 2.0 working - User: @{user.data.username}")
            else:
                logger.error("✗ OAuth 2.0 failed - Cannot get user info")
                return False
        except Exception as e:
            logger.error(f"✗ OAuth 2.0 error: {e}")
            return False
        
        # Test OAuth 1.0a (media upload)
        logger.info("\n2. Testing OAuth 1.0a media upload permissions...")
        test_media = "./test_media.jpg"
        
        if not os.path.exists(test_media):
            logger.error("✗ Test media file not found")
            logger.info("Creating test media file...")
            try:
                from PIL import Image
                img = Image.new('RGB', (100, 100), color='blue')
                img.save(test_media, 'JPEG')
                logger.info("✓ Test media file created")
            except Exception as e:
                logger.error(f"✗ Failed to create test media: {e}")
                return False
        
        try:
            media_id = api.upload_media(test_media)
            if media_id:
                logger.info("✓ OAuth 1.0a working - Media upload successful")
                logger.info("✓ All permissions are correctly configured!")
                return True
            else:
                logger.error("✗ OAuth 1.0a failed - Media upload returned None")
                return False
        except Exception as e:
            error_msg = str(e).lower()
            if "oauth1 app permissions" in error_msg or "403" in error_msg:
                logger.error("✗ OAuth 1.0a permission error detected!")
                logger.error("\n" + "=" * 50)
                logger.error("FIX INSTRUCTIONS:")
                logger.error("=" * 50)
                logger.error("1. Go to: https://developer.twitter.com/en/portal/dashboard")
                logger.error("2. Select your app")
                logger.error("3. Go to 'App permissions' section")
                logger.error("4. Change to 'Read and Write'")
                logger.error("5. Go to 'Keys and tokens' section")
                logger.error("6. Regenerate Access Token and Secret")
                logger.error("7. Update your .env file with new tokens")
                logger.error("=" * 50)
                return False
            else:
                logger.error(f"✗ OAuth 1.0a error: {e}")
                return False
        
    except ValueError as e:
        logger.error(f"✗ Configuration error: {e}")
        logger.error("Please check your .env file contains all required Twitter credentials")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False


def main():
    """Run diagnostic."""
    success = diagnose_oauth_permissions()
    
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✓ All tests passed! Twitter OAuth is working correctly.")
        logger.info("You can now run the main archiver application.")
    else:
        logger.error("✗ Issues detected. Please follow the fix instructions above.")
        logger.error("See TWITTER_OAUTH_FIX.md for detailed guidance.")
    logger.info("=" * 60)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)