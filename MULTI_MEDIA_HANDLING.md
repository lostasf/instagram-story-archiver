# Multi-Media Story Handling

This document explains how the Instagram Story Archiver handles Instagram stories with multiple media items (more than 4 stories per post).

## Overview

Instagram stories can contain multiple media items (images or videos). Previously, the archiver only downloaded and posted the first media item. Now it correctly handles ALL media items in a story.

## Key Changes

### 1. Archive Stage (`archive_story()`)
- **Before**: Downloaded only the first media item
- **After**: Downloads ALL media items from a story
- Stores multiple local paths: `local_media_paths` (list)
- Stores multiple media types: `media_types` (list)
- Maintains backward compatibility with legacy fields

### 2. Post Stage (`post_story()`)
- **Before**: Posted only one tweet with one media item
- **After**: Posts all media items as a Twitter thread

#### Posting Logic

**Batching:**
- Twitter allows up to 4 media items (images, videos, or GIFs) per tweet.
- Media items are batched: 1-4 items = 1 tweet, 5-8 items = 2 tweets, etc.
- This applies even if the story contains a mix of images and videos.
- Each tweet in the batch shows progress: `(1/2)`, `(2/2)` (only if there are multiple tweets).

**Unified Threads:**
- Photos and videos are mixed in the same tweet whenever possible to minimize the total number of tweets in a thread.
- If a story has 2 images and 1 video, they are posted together in a single tweet.
- If a story has 5 items (e.g., 4 images and 1 video), it is split across 2 tweets in the thread.

### 3. Archive Data Structure

```json
{
  "story_id": "123456789",
  "media_count": 5,
  "media_urls": ["url1", "url2", "url3", "url4", "url5"],
  "local_media_paths": ["/path/1.jpg", "/path/2.jpg", ...],
  "media_types": ["image", "image", "image", "image", "image"],
  "tweet_ids": ["tweet1", "tweet2"],
  "taken_at": 1234567890,
  
  // Legacy fields (for backward compatibility)
  "local_media_path": "/path/1.jpg",
  "media_type": "image"
}
```

## Examples

### Example 1: Story with 5 Images
- Archive stage: Downloads all 5 images
- Post stage: Creates 2 tweets
  - Tweet 1: 4 images with caption + "(1/2)"
  - Tweet 2: 1 image with caption + "(2/2)"

### Example 2: Story with 2 Images and 1 Video
- Archive stage: Downloads all 3 media items
- Post stage: Creates 1 tweet
  - Tweet 1: 2 images and 1 video with caption

### Example 3: Story with 3 Videos
- Archive stage: Downloads all 3 videos
- Post stage: Creates 1 tweet
  - Tweet 1: 3 videos with caption

### Example 4: Story with 1 Image
- Archive stage: Downloads 1 image
- Post stage: Creates 1 tweet
  - Tweet 1: 1 image with caption (no progress indicator)

## Backward Compatibility

The changes are fully backward compatible:

1. **Legacy archives**: Old stories with single `local_media_path` will work
2. **Fallback logic**: If `local_media_paths` is missing, uses `local_media_path`
3. **Legacy fields**: Both old and new fields are stored in new archives

## Benefits

1. **Complete archiving**: No media is lost from multi-item stories
2. **Better Twitter threads**: Each story is fully represented
3. **Rate limit efficiency**: Batches images to minimize tweet count
4. **Flexible**: Handles any number of media items

## Testing

Run the test suite to verify multi-media handling:

```bash
python test_multi_media.py
```

This tests:
- Media extraction from Instagram API responses
- Archive data structure for multiple media
- Batch calculation logic for Twitter posts

## Implementation Details

### Key Functions

1. **`story_archiver.archive_story()`**
   - Loops through all media items
   - Downloads and compresses each one
   - Stores all paths in archive

2. **`story_archiver.post_story()`**
   - Retrieves all media paths from archive
   - Determines posting strategy (images vs videos)
   - Creates thread with appropriate batching

3. **`archive_manager.update_story_local_paths()`**
   - New method to update multiple paths
   - Maintains both new and legacy field formats

## Rate Limits

**RapidAPI (Instagram):**
- 1000 requests/month
- No change in usage (same number of API calls)

**Twitter API:**
- 1500 media uploads per 15 minutes
- Multiple media items increase uploads but still within limits
- Thread creation uses standard tweet quotas

## Future Enhancements

Possible improvements:
- Smart video detection for mixed media
- Configurable batch sizes
- Carousel support for related images
- Resume partial uploads on failure
