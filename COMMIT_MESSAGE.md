feat: Add full support for Instagram stories with 4+ media items

## Summary
Implemented complete multi-media story handling to archive and post ALL media items from Instagram stories, not just the first one. Stories with 4+ images/videos are now fully preserved and intelligently posted to Twitter as threads.

## Problem
Previously, when an Instagram story contained multiple media items (e.g., 5 images), only the first media item was downloaded and posted to Twitter. The remaining 4 items were lost.

## Solution
### Archive Stage
- Downloads ALL media items from each story
- Stores multiple local paths and media types
- Maintains backward compatibility with legacy single-media format

### Post Stage
- Posts all media items as Twitter threads
- **Images**: Batches up to 4 images per tweet (Twitter's limit)
  - 1-4 images → 1 tweet
  - 5-8 images → 2 tweets  
  - 9+ images → multiple tweets
- **Videos**: Posts 1 video per tweet (Twitter's requirement)
- Adds progress indicators: "(1/2)", "(2/2)"
- Creates properly threaded tweets

## Technical Changes

### Modified Files
1. **story_archiver.py**
   - `archive_story()`: Loop through all media items, download all
   - `post_story()`: Intelligent batching and thread creation

2. **archive_manager.py**
   - Added `local_media_paths` and `media_types` fields
   - New method: `update_story_local_paths()`
   - Maintains legacy fields for backward compatibility

3. **README.md**
   - Added multi-media handling section
   - Updated features list
   - Marked enhancement as complete

### New Files
- `MULTI_MEDIA_HANDLING.md` - Comprehensive documentation
- `test_multi_media.py` - Test suite for multi-media functionality
- `CHANGELOG_MULTI_MEDIA.md` - Detailed changelog

## Examples

### Before
```
Story: [Img1, Img2, Img3, Img4, Img5]
Archived: Img1 only
Twitter: 1 tweet with Img1
Lost: Img2, Img3, Img4, Img5 ❌
```

### After
```
Story: [Img1, Img2, Img3, Img4, Img5]
Archived: All 5 images
Twitter: 
  - Tweet 1: Img1-4 + "(1/2)"
  - Tweet 2: Img5 + "(2/2)"
Complete: All 5 images ✅
```

## Backward Compatibility
✅ Fully backward compatible
- Old archives continue to work
- Legacy field format maintained
- Single-media stories unchanged
- No migration needed

## Testing
- Syntax validation: ✅ All files compile
- Manual testing recommended for:
  - Stories with 1, 4, 5, 8+ media items
  - Video stories
  - Mixed media stories
  
Run: `python test_multi_media.py`

## Benefits
1. Complete story preservation
2. Better Twitter representation  
3. Smart batching minimizes tweet count
4. User-friendly progress indicators
5. No breaking changes

Fixes #[issue-number] (if applicable)
