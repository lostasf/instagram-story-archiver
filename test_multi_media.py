#!/usr/bin/env python3
"""
Test script to verify multi-media story handling
"""

import logging
import json
import os
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def create_mock_story_data(num_media: int = 5) -> Dict:
    """Create mock Instagram story data with multiple media items"""
    media_items = []
    for i in range(num_media):
        media_items.append({
            'pk': f'test_media_{i}',
            'id': f'test_media_{i}',
            'image_versions2': {
                'candidates': [
                    {
                        'url': f'https://example.com/image_{i}.jpg',
                        'width': 1080,
                        'height': 1920
                    }
                ]
            },
            'taken_at': 1234567890 + i
        })
    
    return {
        'pk': 'test_story_123',
        'id': 'test_story_123',
        'taken_at': 1234567890,
        'items': media_items
    }


def test_instagram_api_extract_media():
    """Test that extract_media_urls correctly extracts all media items"""
    from instagram_api import InstagramAPI
    from config import Config
    
    logger.info("Testing InstagramAPI.extract_media_urls with 5 media items...")
    
    # Create mock config
    os.environ['RAPIDAPI_KEY'] = 'test_key'
    config = Config()
    api = InstagramAPI(config)
    
    # Test with 5 media items
    story_data = create_mock_story_data(5)
    media_list = api.extract_media_urls(story_data)
    
    assert len(media_list) == 5, f"Expected 5 media items, got {len(media_list)}"
    logger.info(f"✓ Correctly extracted {len(media_list)} media items")
    
    for i, media in enumerate(media_list):
        assert media['url'] == f'https://example.com/image_{i}.jpg'
        assert media['type'] == 'image'
    
    logger.info("✓ All media URLs are correct")
    
    return True


def test_archive_data_structure():
    """Test that archive stores multiple media paths correctly"""
    from archive_manager import ArchiveManager
    
    logger.info("Testing ArchiveManager data structure for multiple media...")
    
    # Create temporary archive
    archive_path = './test_archive.json'
    if os.path.exists(archive_path):
        os.remove(archive_path)
    
    manager = ArchiveManager(archive_path, 'test_user')
    
    # Add story with multiple media
    story_data = {
        'media_count': 5,
        'media_urls': [f'https://example.com/image_{i}.jpg' for i in range(5)],
        'tweet_ids': [],
        'taken_at': 1234567890,
        'local_media_paths': [f'/tmp/test_{i}.jpg' for i in range(5)],
        'media_types': ['image'] * 5,
        'local_media_path': '/tmp/test_0.jpg',
        'media_type': 'image',
    }
    
    success = manager.add_story('test_user', 'story_123', story_data)
    assert success, "Failed to add story to archive"
    
    # Verify data
    stats = manager.get_statistics('test_user')
    stories = stats.get('stories', [])
    assert len(stories) == 1, f"Expected 1 story, got {len(stories)}"
    
    story = stories[0]
    assert story['media_count'] == 5
    assert len(story['local_media_paths']) == 5
    assert len(story['media_types']) == 5
    assert story['local_media_path'] == '/tmp/test_0.jpg'  # Legacy field
    
    logger.info("✓ Archive correctly stores multiple media paths")
    
    # Test update_story_local_paths
    manager.update_story_local_paths('test_user', 'story_123', None)
    stats = manager.get_statistics('test_user')
    story = stats['stories'][0]
    assert story['local_media_paths'] is None
    assert story['local_media_path'] is None
    
    logger.info("✓ Archive correctly updates multiple media paths")
    
    # Cleanup
    os.remove(archive_path)
    
    return True


def test_batch_logic():
    """Test the batching logic for posting multiple images"""
    logger.info("Testing batch logic for posting 4+ images...")
    
    # Test cases
    test_cases = [
        (1, 1, "Single image"),
        (3, 1, "3 images (1 tweet)"),
        (4, 1, "4 images (1 tweet)"),
        (5, 2, "5 images (2 tweets)"),
        (8, 2, "8 images (2 tweets)"),
        (9, 3, "9 images (3 tweets)"),
    ]
    
    for num_images, expected_tweets, description in test_cases:
        batch_size = 4
        actual_tweets = (num_images + batch_size - 1) // batch_size
        assert actual_tweets == expected_tweets, \
            f"{description}: Expected {expected_tweets} tweets, got {actual_tweets}"
        logger.info(f"✓ {description}: {actual_tweets} tweet(s)")
    
    return True


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Running multi-media story handling tests")
    logger.info("=" * 60)
    
    tests = [
        ("Instagram API media extraction", test_instagram_api_extract_media),
        ("Archive data structure", test_archive_data_structure),
        ("Batch logic", test_batch_logic),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info("")
        logger.info(f"Running: {test_name}")
        logger.info("-" * 60)
        try:
            result = test_func()
            if result:
                logger.info(f"✓ PASSED: {test_name}")
                passed += 1
            else:
                logger.error(f"✗ FAILED: {test_name}")
                failed += 1
        except Exception as e:
            logger.error(f"✗ FAILED: {test_name}")
            logger.error(f"Error: {e}", exc_info=True)
            failed += 1
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Test Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
