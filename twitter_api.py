import tweepy
import logging
from typing import List, Optional
import os
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
        """
        try:
            logger.info(f"Uploading media: {media_path}")
            
            media = self.v1_client.media_upload(filename=media_path)
            media_id = media.media_id_string
            
            logger.info(f"Media uploaded successfully. ID: {media_id}")
            return media_id
            
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
            logger.error(f"Error posting tweet: {e}")
            return None
    
    def create_thread(self, posts: List[dict]) -> bool:
        """
        Create a thread of tweets.
        Each post dict should contain: 'text', 'media_path' (optional)
        
        Args:
            posts: List of post dictionaries
        
        Returns:
            True if all posts successful, False otherwise
        """
        try:
            logger.info(f"Creating thread with {len(posts)} posts")
            
            reply_to_id = None
            
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
                    return False
                
                reply_to_id = tweet_id
                logger.info(f"Posted tweet {i+1}/{len(posts)} in thread")
            
            logger.info("Thread created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            return False
