import os
import requests
import logging
from typing import Optional, List
from pathlib import Path
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


class MediaManager:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

    def get_cached_media_path(self, media_id: str, media_type: str) -> Optional[str]:
        """Return an existing cached media path for the given media_id/type, if any."""
        file_ext = 'mp4' if media_type == 'video' else 'jpg'
        base_path = os.path.join(self.cache_dir, f"{media_id}.{file_ext}")

        if media_type == 'image':
            compressed_path = os.path.join(self.cache_dir, f"{media_id}_compressed.jpg")
            if os.path.exists(compressed_path):
                return compressed_path

        if os.path.exists(base_path):
            return base_path

        return None

    def download_media(self, url: str, media_id: str, media_type: str) -> Optional[str]:
        """
        Download media from URL and save to cache.

        Args:
            url: URL of the media
            media_id: Unique identifier for the media
            media_type: 'image' or 'video'

        Returns:
            Local file path if successful, None otherwise
        """
        try:
            logger.info(f"Downloading {media_type}: {url[:50]}...")

            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            file_ext = 'mp4' if media_type == 'video' else 'jpg'
            file_path = os.path.join(self.cache_dir, f"{media_id}.{file_ext}")

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(file_path)
            logger.info(f"Downloaded {media_type} to {file_path} ({file_size} bytes)")

            return file_path

        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None
    
    def compress_image(self, image_path: str, max_size_mb: float = 5.0) -> Optional[str]:
        """
        Compress image to fit Twitter's size requirements.
        Twitter supports max 5MB per image.
        
        Args:
            image_path: Path to image file
            max_size_mb: Maximum file size in MB
        
        Returns:
            Path to compressed image, or original if already small enough
        """
        try:
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            
            if file_size_mb <= max_size_mb:
                logger.info(f"Image already within size limit: {file_size_mb:.2f}MB")
                return image_path
            
            logger.info(f"Compressing image from {file_size_mb:.2f}MB")
            
            with Image.open(image_path) as img:
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                
                # Compress
                compressed_path = image_path.replace('.jpg', '_compressed.jpg')
                quality = 85
                
                while quality > 20:
                    img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
                    new_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
                    
                    if new_size_mb <= max_size_mb:
                        logger.info(f"Compressed to {new_size_mb:.2f}MB at quality {quality}")
                        return compressed_path
                    
                    quality -= 5
            
            logger.warning(f"Could not compress image below {max_size_mb}MB")
            return compressed_path
            
        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            return image_path
    
    def cleanup_media(self, file_path: str) -> bool:
        """
        Delete media file from cache and its variants (e.g. compressed version).
        """
        try:
            if not os.path.exists(file_path):
                return False

            # If it's a compressed file, also try to delete the original
            if "_compressed.jpg" in file_path:
                original_path = file_path.replace("_compressed.jpg", ".jpg")
                if os.path.exists(original_path):
                    os.remove(original_path)
                    logger.info(f"Cleaned up original media file: {original_path}")
            
            # If it's an original file, also try to delete the compressed version
            elif file_path.endswith(".jpg") and "_compressed" not in file_path:
                compressed_path = file_path.replace(".jpg", "_compressed.jpg")
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)
                    logger.info(f"Cleaned up compressed media file: {compressed_path}")

            os.remove(file_path)
            logger.info(f"Cleaned up media file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up media: {e}")
            return False
    
    def cleanup_old_media(self, keep_count: int = 100) -> None:
        """
        Remove old media files, keeping only the most recent ones.
        """
        try:
            files = sorted(
                [os.path.join(self.cache_dir, f) for f in os.listdir(self.cache_dir)],
                key=os.path.getctime
            )
            
            if len(files) > keep_count:
                files_to_remove = files[:-keep_count]
                for file_path in files_to_remove:
                    self.cleanup_media(file_path)
                
                logger.info(f"Cleaned up {len(files_to_remove)} old media files")
        except Exception as e:
            logger.error(f"Error cleaning up old media: {e}")
