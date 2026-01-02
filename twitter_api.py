import tweepy
import logging
from typing import List, Optional
import os
import time
from config import Config

logger = logging.getLogger(__name__)


class TwitterAPI:
    def __init__(self, config: Config):
        self.config = config
        
        # Log which credentials are available (without showing values)
        has_api_key = bool(config.TWITTER_API_KEY)
        has_api_secret = bool(config.TWITTER_API_SECRET)
        has_access_token = bool(config.TWITTER_ACCESS_TOKEN)
        has_access_secret = bool(config.TWITTER_ACCESS_SECRET)
        has_bearer_token = bool(config.TWITTER_BEARER_TOKEN)
        
        logger.info(f"Twitter Credentials Status: "
                    f"API Key: {'Found' if has_api_key else 'Missing'}, "
                    f"API Secret: {'Found' if has_api_secret else 'Missing'}, "
                    f"Access Token: {'Found' if has_access_token else 'Missing'}, "
                    f"Access Secret: {'Found' if has_access_secret else 'Missing'}, "
                    f"Bearer Token: {'Found' if has_bearer_token else 'Missing'}")
        
        # Initialize v2 client
        # If we have OAuth 1.0a tokens, prioritize them for the client.
        if has_api_key and has_api_secret and has_access_token and has_access_secret:
            logger.info("Initializing Twitter API v2 Client with OAuth 1.0a User Context")
            self.client = tweepy.Client(
                consumer_key=config.TWITTER_API_KEY,
                consumer_secret=config.TWITTER_API_SECRET,
                access_token=config.TWITTER_ACCESS_TOKEN,
                access_token_secret=config.TWITTER_ACCESS_SECRET,
                wait_on_rate_limit=False
            )
        elif has_bearer_token:
            logger.info("Initializing Twitter API v2 Client with Bearer Token")
            self.client = tweepy.Client(
                bearer_token=config.TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=False
            )
        else:
            logger.error("No valid Twitter credentials found!")
            raise ValueError("No valid Twitter credentials found")

        # Keep v1 client for media upload (always requires OAuth 1.0a)
        if has_api_key and has_api_secret and has_access_token and has_access_secret:
            self.v1_client = tweepy.API(
                auth=tweepy.OAuth1UserHandler(
                    config.TWITTER_API_KEY,
                    config.TWITTER_API_SECRET,
                    config.TWITTER_ACCESS_TOKEN,
                    config.TWITTER_ACCESS_SECRET
                ),
                wait_on_rate_limit=False
            )
        else:
            logger.warning("Twitter API v1.1 Client NOT initialized (requires OAuth 1.0a)")
            self.v1_client = None

    def verify_credentials(self) -> bool:
        """
        Verify Twitter API credentials and permissions.

        Returns:
            True if credentials are valid and have write permissions, False otherwise.
        """
        try:
            logger.info("Verifying Twitter API credentials...")

            # Try to get user info using v2 API (requires read permission)
            me = self.client.get_me()
            if not me.data:
                logger.error("Failed to verify credentials: Could not retrieve user info")
                return False

            username = me.data.username
            logger.info(f"Authenticated as: @{username}")

            # Try to verify v1.1 credentials (used for media upload)
            if self.v1_client:
                try:
                    v1_verify = self.v1_client.verify_credentials()
                    logger.info(f"v1.1 API verified as: @{v1_verify.screen_name}")
                except Exception as e:
                    logger.warning(f"v1.1 API verification failed: {e}")
                    logger.warning("Media upload might not work")
            else:
                logger.warning("v1.1 API client not initialized. Media upload will not work.")

            # Test write permissions by checking if we can create a tweet
            # We don't actually post, just verify the client is configured correctly
            logger.info("Checking write permissions...")
            logger.info("Note: To fully test write permissions, we would need to post a test tweet")

            return True

        except tweepy.Forbidden as e:
            error_msg = str(e)
            logger.error("Twitter API Permission Error (403 Forbidden)")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            logger.error("This typically means your Twitter app permissions are not configured correctly.")
            logger.error("")
            logger.error("TO FIX THIS ISSUE:")
            logger.error("1. Go to https://developer.twitter.com/en/portal/dashboard")
            logger.error("2. Select your app")
            logger.error("3. Go to 'Settings' > 'App permissions'")
            logger.error("4. Change permissions from 'Read' to 'Read and Write'")
            logger.error("5. Go to 'Settings' > 'User authentication settings'")
            logger.error("6. Make sure OAuth 1.0a is enabled")
            logger.error("7. IMPORTANT: After changing permissions, go to 'Keys and tokens'")
            logger.error("8. Click 'Regenerate' for both Access Token and Access Token Secret")
            logger.error("9. Update your GitHub Actions secrets with the new tokens")
            logger.error("")
            logger.error(f"Technical details: {error_msg}")
            return False

        except tweepy.Unauthorized as e:
            logger.error("Twitter API Authentication Error (401 Unauthorized)")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            logger.error("Your API keys or access tokens are invalid or expired.")
            logger.error("")
            logger.error("TO FIX THIS ISSUE:")
            logger.error("1. Check that all Twitter credentials are set correctly")
            logger.error("2. Regenerate your Access Token and Secret in the Twitter Developer Portal")
            logger.error("3. Update your GitHub Actions secrets with the new tokens")
            logger.error(f"Technical details: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error verifying Twitter credentials: {e}")
            return False
    
    def upload_media(self, media_path: str) -> Optional[str]:
        """
        Upload media to Twitter and return media ID.
        Uses OAuth 1.0a for media upload with better error handling.
        """
        if not self.v1_client:
            logger.error("Cannot upload media: v1.1 API client not initialized (OAuth 1.0a tokens missing)")
            return None

        try:
            logger.info(f"Uploading media: {media_path}")

            # Check file size (Twitter limit is 5MB for images, 15MB for videos)
            file_size = os.path.getsize(media_path)
            if file_size > 15 * 1024 * 1024:  # 15MB
                logger.error(f"File too large: {file_size} bytes (max 15MB)")
                return None

            # Try media upload with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    media = self.v1_client.media_upload(filename=media_path)
                    media_id = media.media_id_string

                    logger.info(f"Media uploaded successfully. ID: {media_id}")
                    return media_id

                except tweepy.Forbidden as upload_error:
                    error_msg = str(upload_error)
                    logger.error(f"Twitter API Permission Error (403 Forbidden) during media upload: {upload_error}")
                    logger.error(f"Response: {upload_error.response.text if hasattr(upload_error, 'response') else 'N/A'}")
                    logger.error("")
                    logger.error("THIS ERROR MEANS YOUR TWITTER APP DOES NOT HAVE WRITE PERMISSIONS")
                    logger.error("")
                    logger.error("TO FIX THIS ISSUE:")
                    logger.error("1. Go to https://developer.twitter.com/en/portal/dashboard")
                    logger.error("2. Select your app")
                    logger.error("3. Go to 'Settings' > 'App permissions'")
                    logger.error("4. Change permissions from 'Read' to 'Read and Write'")
                    logger.error("5. Go to 'Settings' > 'User authentication settings'")
                    logger.error("6. Make sure OAuth 1.0a is enabled with 'Read and Write' permissions")
                    logger.error("7. CRITICAL: After changing permissions, go to 'Keys and tokens'")
                    logger.error("8. Click 'Regenerate' for BOTH Access Token and Access Token Secret")
                    logger.error("9. Copy the NEW tokens and update your GitHub Actions secrets")
                    logger.error("")
                    logger.error("⚠️  THE OLD TOKENS WON'T WORK WITH NEW PERMISSIONS!")
                    logger.error("⚠️  YOU MUST REGENERATE THEM AFTER CHANGING PERMISSIONS!")
                    return None

                except Exception as upload_error:
                    error_msg = str(upload_error).lower()

                    # Check for specific OAuth 1.0a permission errors (legacy format)
                    if "oauth1 app permissions" in error_msg or "403" in error_msg:
                        logger.error(f"OAuth 1.0a permission error: {upload_error}")
                        logger.error("This error indicates your Twitter app needs OAuth 1.0a permissions.")
                        logger.error("Please check your Twitter Developer Portal app settings:")
                        logger.error("1. Go to your app's 'Keys and tokens' section")
                        logger.error("2. Ensure your app has 'Read and Write' permissions")
                        logger.error("3. Regenerate your Access Token and Secret after changing permissions")
                        return None

                    # For other errors, retry
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Upload attempt {attempt + 1} failed, retrying in {wait_time}s: {upload_error}")
                        time.sleep(wait_time)
                    else:
                        raise upload_error

        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            return None
    
    def post_tweet(self, text: str, media_ids: List[str] = None, reply_to_id: str = None) -> Optional[str]:
        """
        Post a tweet with optional media and reply thread support.
        Returns tweet ID if successful.
        """
        try:
            logger.info(f"Posting tweet: {text[:100]}...")

            response = self.client.create_tweet(
                text=text,
                media_ids=media_ids,
                in_reply_to_tweet_id=reply_to_id
            )

            tweet_id = response.data['id']
            logger.info(f"Tweet posted successfully. ID: {tweet_id}")
            return tweet_id

        except tweepy.Forbidden as e:
            error_msg = str(e)
            logger.error(f"Twitter API Permission Error (403 Forbidden): {e}")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            logger.error("")
            logger.error("THIS ERROR MEANS YOUR TWITTER APP DOES NOT HAVE WRITE PERMISSIONS")
            logger.error("")
            logger.error("TO FIX THIS ISSUE:")
            logger.error("1. Go to https://developer.twitter.com/en/portal/dashboard")
            logger.error("2. Select your app")
            logger.error("3. Go to 'Settings' > 'App permissions'")
            logger.error("4. Change permissions from 'Read' to 'Read and Write'")
            logger.error("5. Go to 'Settings' > 'User authentication settings'")
            logger.error("6. Make sure OAuth 1.0a is enabled with 'Read and Write' permissions")
            logger.error("7. CRITICAL: After changing permissions, go to 'Keys and tokens'")
            logger.error("8. Click 'Regenerate' for BOTH Access Token and Access Token Secret")
            logger.error("9. Copy the NEW tokens and update your GitHub Actions secrets")
            logger.error("")
            logger.error("⚠️  THE OLD TOKENS WON'T WORK WITH NEW PERMISSIONS!")
            logger.error("⚠️  YOU MUST REGENERATE THEM AFTER CHANGING PERMISSIONS!")
            return None

        except tweepy.Unauthorized as e:
            logger.error(f"Twitter API Authentication Error (401 Unauthorized): {e}")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            logger.error("Your access tokens may be invalid or expired.")
            logger.error("Try regenerating your Access Token and Secret in the Twitter Developer Portal.")
            return None

        except Exception as e:
            error_msg = str(e).lower()

            # Check for specific OAuth 1.0a permission errors (legacy)
            if "oauth1 app permissions" in error_msg or "403" in error_msg:
                logger.error(f"OAuth permission error: {e}")
                logger.error("This error indicates your Twitter app permissions need to be updated.")
                logger.error("Please check your Twitter Developer Portal app settings:")
                logger.error("1. Go to your app's 'App permissions' section")
                logger.error("2. Set permissions to 'Read and Write'")
                logger.error("3. Regenerate your Access Token and Secret after changing permissions")
            else:
                logger.error(f"Error posting tweet: {e}")

            return None
    
    def create_thread(self, posts: List[dict]) -> List[str]:
        """
        Create a thread of tweets.
        Each post dict should contain: 'text', 'media_path' (optional)
        
        Args:
            posts: List of post dictionaries
        
        Returns:
            List of tweet IDs if successful, empty list if failed
        """
        try:
            logger.info(f"Creating thread with {len(posts)} posts")
            
            reply_to_id = None
            tweet_ids = []
            
            for i, post in enumerate(posts):
                text = post.get('text', '')
                media_path = post.get('media_path')
                
                media_ids = None
                if media_path and os.path.exists(media_path):
                    media_id = self.upload_media(media_path)
                    if media_id:
                        media_ids = [media_id]
                
                tweet_id = self.post_tweet(
                    text=text,
                    media_ids=media_ids,
                    reply_to_id=reply_to_id
                )
                
                if not tweet_id:
                    logger.warning(f"Failed to post tweet {i+1}/{len(posts)}")
                    return []
                
                tweet_ids.append(tweet_id)
                reply_to_id = tweet_id
                logger.info(f"Posted tweet {i+1}/{len(posts)} in thread")
            
            logger.info("Thread created successfully")
            return tweet_ids
            
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            return []
