# Instagram Stories Cache & UploadTime Implementation

## Summary of Changes

This implementation adds the `uploadTime` attribute to archive.json and rewrites the posting logic to ensure stories are cached in the GitHub repository and posted at the correct time (one day after upload).

## Key Changes Made

### 1. Archive Reset
- **Reset archive.json** to empty state (schema_version: 2, empty accounts)
- **Cleared media_cache/** directory (only keeping .gitkeep)

### 2. ArchiveManager Updates (`archive_manager.py`)
- **Added `uploadTime` field** to story entries in `add_story()` method
- The `uploadTime` is stored from story_data (which comes from Instagram's `taken_at` field)
- Maintains backward compatibility with existing `taken_at` field

### 3. StoryArchiver Updates (`story_archiver.py`)

#### `archive_story()` Method
- **Extracts `uploadTime`** from Instagram story's `taken_at` field
- **Includes `uploadTime`** in the archive_data when saving to archive.json
- Downloads and caches media files to media_cache/ directory
- Stores with `tweet_ids: []` initially (not yet posted)

#### `_sync_cache_only_stories()` Method
- **Includes `uploadTime`** in backfilled archive entries
- Uses file modification time as uploadTime for cached-only stories

#### `post_pending_stories()` Method (MAJOR REWRITE)
New logic:
1. Gets current date in GMT+7 timezone
2. Calculates `today_start` (midnight of current day)
3. Separates unposted stories into two groups:
   - **Stories to post**: `uploadTime < today_start` (uploaded before today)
   - **Stories planned**: `uploadTime >= today_start` (uploaded today)
4. **Posts** all stories in the "to post" group
5. **Logs** stories in the "planned" group with message "(planned for next day)"
6. After posting successfully:
   - Updates `tweet_ids` in archive.json
   - Deletes media files from media_cache/
   - Clears `local_media_paths` in archive.json

### 4. GitHub Actions Workflow Updates (`.github/workflows/archive-stories.yml`)
- **Improved media_cache handling**: Only adds media_cache/ to git if there are files in it
- This prevents empty commits when media_cache is clean

## GitHub Action Flow

### Step 1: Fetch Instagram Stories
- Calls `archive_all_stories()` for all configured users
- Downloads media files to `media_cache/`
- Adds new stories to `archive.json` with:
  - `uploadTime`: Unix timestamp from Instagram's `taken_at`
  - `storyId`: Unique story identifier
  - `mediafiles`: URLs and local paths
  - `tweet_ids`: Empty array `[]` (not yet posted)

### Step 2: Check for Stories to Post
- Calls `post_pending_stories()`
- Filters unposted stories by `uploadTime < today`
- Posts stories that were uploaded **before the current day**
- Skips stories uploaded **today** (logs them as planned for tomorrow)

### Step 3: After Posting
- Updates `tweet_ids` in `archive.json` for posted stories
- Deletes media files from `media_cache/`
- Clears `local_media_paths` in `archive.json`

### Step 4: Commit Changes
- Commits `archive.json`, `archiver.log`, and `media_cache/` to repository
- Media files are tracked in GitHub until they are posted

## Example Timeline

### Day 1 (January 1st)
- Instagram stories uploaded at 10:00 AM GMT+7
- GitHub Action runs at 12:00 PM GMT+7
- Stories are cached with `uploadTime = 10:00 AM timestamp`
- Stories are NOT posted (same day)
- Log shows: "Story XYZ uploaded at 10:00 AM (planned for next day)"

### Day 2 (January 2nd)
- GitHub Action runs at 8:00 AM GMT+7
- `today_start` = 12:00 AM January 2nd
- Stories from January 1st have `uploadTime < today_start`
- Stories are posted to Twitter
- Media files deleted from `media_cache/`
- `tweet_ids` updated in `archive.json`

## Benefits

1. **No race conditions**: Stories are only posted 1 day after upload
2. **Persistent cache**: Media files stored in GitHub repository survive CI/CD restarts
3. **Clean tracking**: Posted stories have media deleted, reducing repository size
4. **Clear logging**: Easy to see which stories are pending vs planned
5. **Backward compatible**: Works with existing archive entries

## Troubleshooting

If stories are not posting:
1. Check `archive.json` for `uploadTime` field
2. Verify `uploadTime < today_start` condition in logs
3. Ensure media files exist in `media_cache/`
4. Check that `tweet_ids` is empty for unposted stories

If media files accumulate:
1. Check if `post_story()` is failing (errors in logs)
2. Verify Twitter API credentials are valid
3. Check if media files are being uploaded successfully
