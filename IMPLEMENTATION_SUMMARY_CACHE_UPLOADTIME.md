# Implementation Summary: Instagram Stories Cache & UploadTime Logic

## Overview
This implementation adds the `uploadTime` attribute to archive.json and rewrites the posting logic to ensure stories are cached in the GitHub repository and posted at the correct time (one day after upload).

## Changes Made

### 1. Archive Reset ✅
- **Reset archive.json** to empty state with `schema_version: 2` and empty `accounts` object
- **Cleared media_cache/** directory (only keeping .gitkeep)

### 2. ArchiveManager (`archive_manager.py`)

#### Fixed Bug in `_get_account()` Method
**Problem:** The method was creating a deep copy of account data and overwriting `archived_stories` with an empty list.

**Solution:** Changed to merge defaults into existing account data without overwriting existing fields:
```python
def _get_account(self, instagram_username: Optional[str]) -> Dict[str, Any]:
    username = self._account_key(instagram_username)
    accounts = self.data.setdefault('accounts', {})
    if username not in accounts or not isinstance(accounts.get(username), dict):
        accounts[username] = _empty_account()
    else:
        # Merge existing account with defaults, preserving existing data
        existing = accounts[username]
        for key, value in _empty_account().items():
            if key not in existing:
                existing[key] = value
    return accounts[username]
```

#### Added `uploadTime` Field to `add_story()` Method
```python
entry: Dict[str, Any] = {
    'story_id': story_id_str,
    'instagram_username': instagram_username,
    'archived_at': datetime.now().isoformat(),
    'uploadTime': story_data.get('uploadTime') or story_data.get('taken_at'),  # NEW
    'media_count': story_data.get('media_count', 0),
    'tweet_ids': story_data.get('tweet_ids', []),
    'media_urls': story_data.get('media_urls', []),
    'taken_at': story_data.get('taken_at'),
    'local_media_path': story_data.get('local_media_path'),
    'media_type': story_data.get('media_type'),
    'local_media_paths': story_data.get('local_media_paths', []),
    'media_types': story_data.get('media_types', []),
}
```

### 3. StoryArchiver (`story_archiver.py`)

#### Updated `archive_story()` Method
**Change:** Extract `uploadTime` from Instagram story's `taken_at` field and include it in archive_data:
```python
taken_at = int(story_data.get('taken_at', 0) or 0)
uploadTime = taken_at  # uploadTime is the same as taken_at from Instagram API

# ... media download code ...

# Save to archive with all media paths
archive_data = {
    'uploadTime': uploadTime,  # NEW
    'media_count': len(media_list),
    'media_urls': [m['url'] for m in media_list],
    'tweet_ids': [],  # Not posted yet
    'taken_at': taken_at,
    'local_media_paths': local_media_paths,
    'media_types': media_types,
    # Keep legacy fields for backward compatibility
    'local_media_path': local_media_paths[0] if local_media_paths else None,
    'media_type': media_types[0] if media_types else 'image',
}
```

#### Updated `_sync_cache_only_stories()` Method
**Change:** Include `uploadTime` in backfilled archive entries for cached-only stories:
```python
archive_data = {
    'uploadTime': taken_at,  # NEW
    'media_count': len(local_media_paths),
    'media_urls': [],
    'tweet_ids': [],
    'taken_at': taken_at,
    'local_media_paths': local_media_paths,
    'media_types': media_types,
    'local_media_path': local_media_paths[0] if local_media_paths else None,
    'media_type': media_types[0] if media_types else 'image',
}
```

#### Completely Rewrote `post_pending_stories()` Method
**New Logic:**
1. Gets current date in GMT+7 timezone
2. Calculates `today_start` (midnight of current day)
3. Separates unposted stories into two groups:
   - **Stories to post**: `uploadTime < today_start` (uploaded before today)
   - **Stories planned**: `uploadTime >= today_start` (uploaded today)
4. Posts all stories in the "to post" group
5. Logs stories in the "planned" group with message "(planned for next day)"
6. After posting successfully, media files are deleted by `post_story()` method

**Key Features:**
- Only posts stories uploaded on or before the previous day
- Stories uploaded today are logged but not posted until tomorrow
- Clear logging to distinguish between "to post" and "planned" stories
- Backward compatibility with stories that don't have `uploadTime` (falls back to `taken_at`)

### 4. GitHub Actions Workflow (`.github/workflows/archive-stories.yml`)
**Change:** Improved media_cache handling to only add directory if there are files:
```yaml
- name: Commit archive changes
  if: success()
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    # Add files to track - including new untracked files
    git add archive.json archiver.log || true
    # Add media_cache directory if there are files in it
    if [ -n "$(find media_cache -type f ! -name '.gitkeep')" ]; then
      git add media_cache/
    fi
    # Check if there are changes (including new files)
    git diff --quiet && git diff --cached --quiet || git commit -m "chore: update archive, logs and media cache [skip ci]"
```

## GitHub Action Flow

### Step 1: Fetch Instagram Stories
- Calls `archive_all_stories()` for all configured users
- Downloads media files to `media_cache/`
- Adds new stories to `archive.json` with:
  - `uploadTime`: Unix timestamp from Instagram's `taken_at`
  - `storyId`: Unique story identifier
  - `mediafiles`: URLs and local paths
  - `tweet_ids`: Empty array `[]` (not yet posted)
- **Media files are now tracked in GitHub repository**

### Step 2: Check for Stories to Post
- Calls `post_pending_stories()`
- Filters unposted stories by `uploadTime < today_start`
- Posts stories that were uploaded **before the current day**
- Skips stories uploaded **today** (logs them as planned for tomorrow)

### Step 3: After Posting
- Updates `tweet_ids` in `archive.json` for posted stories
- Deletes media files from `media_cache/`
- Clears `local_media_paths` in `archive.json`

### Step 4: Commit Changes
- Commits `archive.json`, `archiver.log`, and `media_cache/` to repository
- Only commits `media_cache/` if there are files in it

## Example Timeline

### Day 1 (January 1st) - Stories Uploaded at 10:00 AM GMT+7
- Instagram stories uploaded
- GitHub Action runs at 12:00 PM GMT+7
- Stories are cached with `uploadTime = 10:00 AM timestamp`
- Stories are **NOT posted** (same day)
- Log shows: "Story XYZ uploaded at 10:00 AM (planned for next day)"
- Media files are committed to GitHub repository

### Day 2 (January 2nd) - GitHub Action Runs at 8:00 AM GMT+7
- `today_start` = 12:00 AM January 2nd
- Stories from January 1st have `uploadTime < today_start`
- Stories are posted to Twitter
- Media files deleted from `media_cache/`
- `tweet_ids` updated in `archive.json`
- Only `archive.json` and `archiver.log` are committed (media files deleted)

## Archive.json Schema

### Story Entry Structure
```json
{
  "story_id": "3771310573556982250",
  "instagram_username": "jkt48.gendis",
  "archived_at": "2026-01-01T10:20:45.743482",
  "uploadTime": 1767305241,
  "media_count": 1,
  "tweet_ids": [],
  "media_urls": [
    "https://scontent.cdninstagram.com/..."
  ],
  "taken_at": 1767305241,
  "local_media_paths": [
    "./media_cache/jkt48.gendis_3771310573556982250_0.jpg"
  ],
  "media_types": ["image"]
}
```

### Key Fields
- `uploadTime`: Unix timestamp when the story was uploaded to Instagram (GMT+7)
- `archived_at`: ISO datetime when the story was added to archive
- `tweet_ids`: Array of tweet IDs (empty if not yet posted)
- `local_media_paths`: Array of local file paths (empty after posting)

## Benefits

1. **No race conditions**: Stories are only posted 1 day after upload
2. **Persistent cache**: Media files stored in GitHub repository survive CI/CD restarts
3. **Clean tracking**: Posted stories have media deleted, reducing repository size
4. **Clear logging**: Easy to see which stories are pending vs planned
5. **Backward compatible**: Works with existing archive entries
6. **Bug fix**: Fixed critical bug in `_get_account()` that was preventing stories from being saved

## Testing

All changes have been verified with comprehensive tests:
- ✅ ArchiveManager saves and retrieves `uploadTime` correctly
- ✅ Stories are filtered by `uploadTime < today` correctly
- ✅ GitHub Action workflow logic is correct
- ✅ All Python files compile without errors
- ✅ Bug fix in `_get_account()` prevents data loss

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

## Files Modified

1. `archive.json` - Reset to empty state
2. `media_cache/` - Cleared all files (kept .gitkeep)
3. `archive_manager.py` - Added `uploadTime` field, fixed `_get_account()` bug
4. `story_archiver.py` - Updated `archive_story()`, `_sync_cache_only_stories()`, and completely rewrote `post_pending_stories()`
5. `.github/workflows/archive-stories.yml` - Improved media_cache handling

## Documentation

Created:
- `UPLOADTIME_CHANGES.md` - Detailed explanation of changes
- `IMPLEMENTATION_SUMMARY_CACHE_UPLOADTIME.md` - This document

## Next Steps

When the GitHub Action runs:
1. It will fetch new Instagram stories and cache them
2. Stories uploaded on the same day will be logged as "planned for next day"
3. Stories from the previous day will be posted automatically
4. Media files will be committed to the repository until posted
5. After posting, media files will be deleted and only metadata will remain
