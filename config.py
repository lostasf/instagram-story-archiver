import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
    RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'instagram120.p.rapidapi.com')
    
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
    
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', 'jkt48.gendis')
    CHECK_INTERVAL_HOURS = int(os.getenv('CHECK_INTERVAL_HOURS', '1'))
    ARCHIVE_DB_PATH = os.getenv('ARCHIVE_DB_PATH', './archive.json')
    MEDIA_CACHE_DIR = os.getenv('MEDIA_CACHE_DIR', './media_cache')
    
    def validate(self):
        required = [
            'RAPIDAPI_KEY',
            'TWITTER_API_KEY',
            'TWITTER_API_SECRET',
            'TWITTER_ACCESS_TOKEN',
            'TWITTER_ACCESS_SECRET',
            'TWITTER_BEARER_TOKEN'
        ]
        missing = [key for key in required if not getattr(self, key)]
        if missing:
            raise ValueError(f"Missing configuration: {', '.join(missing)}")
