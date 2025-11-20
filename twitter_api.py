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
        self.client = tweepy.Client(
            bearer_token=config.TWITTER_BEARER_TOKEN,
            consumer_key=config.TWITTER_API_KEY,
            consumer_secret=config.TWITTER_API_SECRET,
            access_token=config.TWITTER_ACCESS_TOKEN,
            access_token_secret=config.TWITTER_ACCESS_SECRET,
            wait_on_rate_limit=True
        )
        
        # Keep v1 client only for media upload as fallback
        self.v1_client = tweepy.API(
            auth=tweepy.OAuth1UserHandler(
                config.TWITTER_API_KEY,
                config.TWITTER_API_SECRET,
                config.TWITTER_ACCESS_TOKEN,
                config.TWITTER_ACCESS_SECRET
            ),
            wait_on_rate_limit=True
        )
    
    def upload_media(self, media_path: str) -> Optional[str]:
        """
        Upload media to Twitter and return media ID.
        Uses OAuth 1.0a for media upload with better error handling.
        """
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
                    
                except Exception as upload_error:
                    error_msg = str(upload_error).lower()
                    
                    # Check for specific OAuth 1.0a permission errors
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
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for specific permission errors
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
