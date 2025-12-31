# Developer Notes - Multi-Media Story Support

## Quick Reference

### Archive Data Structure

**New format (supports multiple media):**
```python
{
    'story_id': '123456789',
    'media_count': 5,
    'media_urls': ['url1', 'url2', 'url3', 'url4', 'url5'],
    'local_media_paths': ['/path/1.jpg', '/path/2.jpg', '/path/3.jpg', '/path/4.jpg', '/path/5.jpg'],
    'media_types': ['image', 'image', 'image', 'image', 'image'],
    'tweet_ids': ['tweet1', 'tweet2'],
    'taken_at': 1234567890,
    # Legacy fields (maintained for backward compatibility)
    'local_media_path': '/path/1.jpg',
    'media_type': 'image'
}
```

### Key Code Sections

#### Downloading All Media (story_archiver.py)
```python
# Download and prepare ALL media items
local_media_paths = []
media_types = []

for idx, media in enumerate(media_list):
    media_path = self.media_manager.download_media(
        media['url'],
        f"{username}_{story_id}_{idx}",
        media['type'],
    )
    if not media_path:
        logger.warning(f"Failed to download media {idx}, continuing...")
        continue

    if media['type'] == 'image':
        media_path = self.media_manager.compress_image(media_path)
    
    local_media_paths.append(media_path)
    media_types.append(media['type'])
```

#### Posting with Batching (story_archiver.py)
```python
# Post all media as a thread
# Twitter allows up to 4 images per tweet or 1 video per tweet
tweet_ids = []

# Check if we have videos (videos must be posted one per tweet)
has_video = any(t == 'video' for t in media_types if t)

if has_video:
    # Post each media item separately
    for idx, media_path in enumerate(media_paths):
        media_id = self.twitter_api.upload_media(media_path)
        tweet_text = caption if idx == 0 else f"{caption}\n({idx + 1}/{len(media_paths)})"
        tweet_id = self.twitter_api.post_tweet(
            text=tweet_text,
            media_ids=[media_id],
            reply_to_id=last_tweet_id,
        )
        tweet_ids.append(tweet_id)
        last_tweet_id = tweet_id
else:
    # All images - batch up to 4 per tweet
    batch_size = 4
    for batch_idx in range(0, len(media_paths), batch_size):
        batch_paths = media_paths[batch_idx:batch_idx + batch_size]
        media_ids = [self.twitter_api.upload_media(p) for p in batch_paths]
        
        if len(media_paths) > batch_size:
            batch_num = batch_idx // batch_size + 1
            total_batches = (len(media_paths) + batch_size - 1) // batch_size
            tweet_text = f"{caption}\n({batch_num}/{total_batches})"
        else:
            tweet_text = caption
        
        tweet_id = self.twitter_api.post_tweet(
            text=tweet_text,
            media_ids=media_ids,
            reply_to_id=last_tweet_id,
        )
        tweet_ids.append(tweet_id)
        last_tweet_id = tweet_id
```

### Twitter Limits

| Media Type | Max Per Tweet | Notes |
|------------|---------------|-------|
| Images | 4 | Can be batched together |
| Videos | 1 | Must be separate tweets |
| GIFs | 1 | Treated as video |
| Image size | 5 MB | Auto-compressed by media_manager |
| Video size | 512 MB | Not compressed (future enhancement) |

### Batch Calculation

```python
# Calculate number of tweets needed for N images
def calculate_tweet_count(num_images, batch_size=4):
    return (num_images + batch_size - 1) // batch_size

# Examples:
calculate_tweet_count(1)  # 1 tweet
calculate_tweet_count(4)  # 1 tweet
calculate_tweet_count(5)  # 2 tweets
calculate_tweet_count(8)  # 2 tweets
calculate_tweet_count(9)  # 3 tweets
```

### Testing Scenarios

1. **Single Image Story**
   - Expected: 1 tweet, no progress indicator
   
2. **Four Images Story**
   - Expected: 1 tweet with 4 images, no progress indicator
   
3. **Five Images Story**
   - Expected: 2 tweets
   - Tweet 1: 4 images + "(1/2)"
   - Tweet 2: 1 image + "(2/2)"
   
4. **Eight Images Story**
   - Expected: 2 tweets
   - Tweet 1: 4 images + "(1/2)"
   - Tweet 2: 4 images + "(2/2)"
   
5. **Three Videos Story**
   - Expected: 3 tweets
   - Tweet 1: 1 video + "(1/3)"
   - Tweet 2: 1 video + "(2/3)"
   - Tweet 3: 1 video + "(3/3)"

### Common Pitfalls

❌ **Don't**: Batch videos with images
```python
# Wrong - Twitter doesn't support this
media_ids = [image_id, video_id, image_id]
```

✅ **Do**: Handle them separately
```python
# Correct
if has_video:
    # Post each media individually
```

❌ **Don't**: Exceed 4 images per tweet
```python
# Wrong - Twitter limit is 4
media_ids = [img1, img2, img3, img4, img5]
```

✅ **Do**: Batch in groups of 4
```python
# Correct
for batch in batches_of_4(media_ids):
    post_tweet(media_ids=batch)
```

### Debugging Tips

1. **Check media_list length**
   ```python
   logger.info(f"Found {len(media_list)} media items")
   ```

2. **Verify all downloads succeeded**
   ```python
   logger.info(f"Downloaded {len(local_media_paths)} of {len(media_list)} items")
   ```

3. **Monitor tweet creation**
   ```python
   logger.info(f"Posted {len(tweet_ids)} tweets for story {story_id}")
   ```

4. **Check archive data**
   ```python
   stats = archive_manager.get_statistics(username)
   story = next(s for s in stats['stories'] if s['story_id'] == story_id)
   logger.info(f"Archive has {len(story['local_media_paths'])} paths")
   ```

### Performance Considerations

- **Download time**: ~2-5 seconds per media item
- **Upload time**: ~3-7 seconds per media item  
- **Total time for 5 images**: ~40-60 seconds
- **Rate limits**: 1500 media uploads per 15 minutes (plenty of headroom)

### Future Enhancement Ideas

1. **Parallel downloads**: Use `asyncio` or `threading`
2. **Smart grouping**: Group related images in same tweet
3. **Video optimization**: Compress large videos
4. **Resume on failure**: Save progress and resume
5. **Carousel mode**: Single tweet with carousel for related images
6. **Configurable batch size**: Allow users to set batch size < 4

### Migration Notes

**No migration needed** - the code handles both formats:

```python
# Handles new format
media_paths = story_entry.get('local_media_paths', [])

# Falls back to legacy format if new format not present
if not media_paths:
    legacy_path = story_entry.get('local_media_path')
    if legacy_path:
        media_paths = [legacy_path]
```

### API Quota Impact

- **Instagram API**: No change (same API call returns all media)
- **Twitter Media Upload**: Increases proportionally to media count
  - 1 media → 1 upload call
  - 5 media → 5 upload calls
- **Twitter Post Tweet**: Increases based on batching
  - 1-4 images → 1 tweet call
  - 5-8 images → 2 tweet calls

### Error Recovery

The implementation is resilient to partial failures:

```python
# If media download fails, continue with others
if not media_path:
    logger.warning(f"Failed to download media {idx}, continuing...")
    continue  # Don't fail entire story

# Only fail if ALL media downloads failed
if not local_media_paths:
    logger.error(f"Failed to download any media")
    return False
```
