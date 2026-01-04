# Developer Notes

Technical documentation for developers working on this codebase.

## Architecture Overview

### Core Components

**main.py** - Entry point with CLI flags
- `--fetch-only`: Archive stories only, don't post
- `--post-daily`: Post stories from previous days grouped by day
- `--status`: Show archive statistics
- `--story-id`: Archive a specific story
- `--username`: Specify Instagram username for --story-id
- `--verify-twitter`: Verify Twitter API credentials and permissions

**Config** (config.py) - Loads configuration from environment variables
- Validates required API keys
- Manages Instagram usernames list
- Handles thread configuration per account

**StoryArchiver** (story_archiver.py) - Main orchestration
- Coordinates InstagramAPI, MediaManager, ArchiveManager, TwitterAPI
- Implements archive and posting logic
- Handles multi-media batching and threading

**InstagramAPI** (instagram_api.py) - Instagram API wrapper (via RapidAPI)
- Fetches stories from accounts
- Extracts media URLs and metadata
- Returns story list with `taken_at` timestamp (key field)

**MediaManager** (media_manager.py) - Media download and processing
- Downloads media from URLs to `media_cache/`
- Compresses images to under 5MB (Twitter limit)
- Manages cache cleanup

**ArchiveManager** (archive_manager.py) - JSON database
- Reads/writes `archive.json`
- Tracks stories with `taken_at` and `tweet_ids`
- Provides statistics and history

**TwitterAPI** (twitter_api.py) - Twitter API wrapper
- Uploads media (v1.1)
- Posts tweets (v2)
- Creates threaded replies

## Key Logic

### Archive Flow (--fetch-only)

1. Load `archive.json`
2. For each Instagram account:
   - Fetch stories from Instagram API
   - For each story:
     - Check if already archived (by story_id)
     - Download all media items to `media_cache/`
     - Compress images if needed
     - Save to `archive.json` with `taken_at` timestamp
     - Log as "planned for next day" if `taken_at` >= today (UTC+7)
3. Commit `archive.json` to git

### Post Flow (--post-daily)

1. Load `archive.json`
2. For each Instagram account:
   - Find unposted stories: `tweet_ids` is empty AND `taken_at` < today (UTC+7)
   - Group stories by day (using `taken_at` date in UTC+7)
   - For each day:
     - Create/reply to anchor tweet (customizable per account)
     - Batch up to 4 media items per tweet
     - Post tweets with progress indicators: `(1/2)`, `(2/2)`, etc.
     - Update `archive.json` with `tweet_ids`
3. Delete media files from `media_cache/` after successful posting
4. Commit `archive.json` to git

### Timezone Handling

**Critical**: All posting logic uses UTC+7 timezone.

- Instagram's `taken_at` is a Unix timestamp (UTC)
- Convert to UTC+7 for "previous days" check
- `taken_at < today (UTC+7)` means story is eligible for posting
- Stories uploaded today (UTC+7) are NOT posted until tomorrow

Example:
- Story uploaded at 2024-01-15 23:00 UTC = 2024-01-16 06:00 UTC+7
- If today (UTC+7) is 2024-01-16, this story will NOT post (same day)
- Will post tomorrow when today becomes 2024-01-17 (UTC+7)

### Multi-Media Batching

Twitter allows up to 4 media items per tweet (images or videos).

**Archive stage**: Downloads ALL media items from a story, stores in `local_media_paths` array.

**Post stage**:
```python
# Group media into batches of up to 4
batch_size = 4
for i in range(0, len(media_paths), batch_size):
    batch = media_paths[i:i + batch_size]
    # Upload all media in batch
    media_ids = [twitter_api.upload_media(path) for path in batch]
    # Post tweet with all media
    tweet_id = twitter_api.post_tweet(text, media_ids, reply_to_id)
```

If story has 5 media items:
- Tweet 1: 4 items + caption + "(1/2)"
- Tweet 2: 1 item + caption + "(2/2)"
- Both tweets are in the same thread

## Archive Database Schema

`archive.json` structure:

```json
{
  "schema_version": 2,
  "accounts": {
    "username": {
      "anchor_tweet_id": "1234567890",
      "last_tweet_id": "1234567899",
      "last_check": "2024-01-15T10:30:00.123456",
      "archived_stories": [
        {
          "story_id": "2921414441985452983",
          "instagram_username": "jkt48.gendis",
          "archived_at": "2024-01-15T10:30:00.123456",
          "taken_at": 1705305600,  // Unix timestamp (UTC) - when the story was uploaded to Instagram
          "media_count": 3,
          "media_urls": ["url1", "url2", "url3"],
          "local_media_path": "path1.jpg",  // Legacy field (single path)
          "media_type": "image",  // Legacy field (single type)
          "local_media_paths": ["path1.jpg", "path2.jpg", "path3.jpg"],  // Array (preferred)
          "media_types": ["image", "image", "video"],  // Array (preferred)
          "tweet_ids": ["1234567899"]  // Empty if not posted
        }
      ]
    }
  }
}
```

**Key fields**:
- `taken_at`: Unix timestamp from Instagram API (UTC) - used for "next day" posting logic
- `tweet_ids`: Array of tweet IDs (empty = not posted yet)
- `local_media_paths`: Array of downloaded media file paths (preferred over legacy `local_media_path`)
- `media_types`: Array of media types ("image" or "video") (preferred over legacy `media_type`)

## GitHub Actions Integration

### Two Workflows

**archive-stories.yml**:
- Schedule: Every 8 hours (`0 */8 * * *` UTC)
- Command: `python main.py --fetch-only`
- Purpose: Fetch and archive new stories
- Commits: `archive.json` and `archiver.log`

**post-stories.yml**:
- Schedule: Daily at 00:00 UTC+7 (`0 17 * * *` UTC)
- Command: `python main.py --post-daily`
- Purpose: Post stories from previous days
- Commits: `archive.json` (with tweet_ids) and `archiver.log`

### Why Separate?

1. **Frequency**: Archive runs every 8h to catch stories before they expire (24h on Instagram)
2. **Organization**: Post runs once daily to post complete days together
3. **Reliability**: Separation avoids rate limiting conflicts
4. **Control**: Can manually trigger archive or post independently

## CLI Flags Reference

| Flag | Purpose | Use Case |
|------|---------|-----------|
| `--fetch-only` | Archive only, no posting | Archive workflow |
| `--post-daily` | Post stories from previous days grouped by day | Post workflow |
| `--status` | Show archive statistics | Monitoring |
| `--story-id` | Archive specific story | Testing/debugging |
| `--username` | Specify Instagram username | With --story-id |
| `--verify-twitter` | Verify Twitter API credentials | Troubleshooting |
| `--post` | Post all pending stories | Legacy (not used in workflows) |
| `--archive-only` | Same as --fetch-only | Alias |

## Error Handling

All components use try-except with logging:

```python
try:
    result = some_operation()
    logger.info(f"Success: {result}")
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # Continue processing if possible
```

**Graceful degradation**:
- If one media download fails, continue with others
- If one story fails, continue with next story
- If one account fails, continue with next account
- Only fail entire run if critical error (config, API auth)

## Testing

### Unit Tests

No formal unit tests yet. Use manual testing:

```bash
# Test configuration and API connections
python test_setup.py

# Test Twitter OAuth specifically
python diagnose_twitter_oauth.py
```

### Test Scripts

**test_setup.py**: Verifies
- Configuration loading
- Instagram API connectivity
- Twitter API authentication

**diagnose_twitter_oauth.py**: Tests
- Twitter API v2 tweet posting
- Twitter API v1.1 media upload
- OAuth permissions

**--verify-twitter flag**: Quick credential verification
```bash
python main.py --verify-twitter
```
Checks:
- Twitter API v2 authentication
- Twitter API v1.1 authentication
- Read permissions
- Write permissions (via error handling)

## Common Modifications

### Change Posting Time

Edit `.github/workflows/post-stories.yml`:

```yaml
on:
  schedule:
    - cron: '0 17 * * *'  # 00:00 UTC+7 = 17:00 UTC
```

To change to 09:00 UTC+7:
```yaml
cron: '0 2 * * *'  # 09:00 UTC+7 = 02:00 UTC
```

### Change Archive Frequency

Edit `.github/workflows/archive-stories.yml`:

```yaml
on:
  schedule:
    - cron: '0 */8 * * *'  # Every 8 hours
```

To change to every 6 hours:
```yaml
cron: '0 */6 * * *'  # Every 6 hours
```

### Change Media Batch Size

Edit `story_archiver.py`, find `post_pending_stories_daily()` method:

```python
batch_size = 4  # Change this value
```

Note: Twitter's limit is 4, so don't increase above 4.

### Add Custom Caption Template

Edit `config.py`, find `get_story_caption()` method:

```python
def get_story_caption(self, username: str, upload_time: datetime) -> str:
    date_str = upload_time.strftime('%d/%m/%Y')

    if 'gendis' in username.lower():
        return f"Instagram Story @Gendis_JKT48\n{date_str}\n\n#Mantrajiva"

    if 'lana' in username.lower():
        return f"Instagram Story @Lana_JKT48\n{date_str}\n\n#LanaJKT48"

    return f"Instagram Story @{username}\n{date_str}"
```

## Performance Considerations

**Memory**: ~100-200MB for typical operations
**Disk**: ~50-100MB/month for media cache (auto-cleaned after posting)
**Network**: ~1-2 minutes per story depending on media size
**API Calls**: ~10-15 per story (check + fetch + media download + upload + post)

## Rate Limits

| Service | Limit | Impact |
|---------|-------|--------|
| Instagram API | 1000/month | ~3 requests/day at 8h interval = ~90/month |
| Twitter Media Upload | 1500/15min | ~5-10 uploads per run (well under limit) |
| Twitter Post Tweet | ~300/15min | ~5-10 posts per run (well under limit) |

## Debugging Tips

### Enable Debug Logging

Edit `main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[...],
)
```

### Check Archive State

```bash
# View archive as JSON
python -m json.tool archive.json

# Check specific account
python -c "import json; print(json.dumps(json.load(open('archive.json'))['accounts']['jkt48.gendis'], indent=2))"

# Count unposted stories
python -c "import json; data=json.load(open('archive.json')); print(sum(1 for s in data['accounts']['jkt48.gendis']['archived_stories'] if not s['tweet_ids']))"
```

### Test Without Posting

```bash
# Archive only (no posting)
python main.py --fetch-only

# Check what would be posted
python main.py --status
```

## Adding Features

### Add New Instagram Account

1. Add to environment variables:
   ```bash
   INSTAGRAM_USERNAMES=jkt48.gendis,jkt48.lana.a,new_account
   ```

2. Add caption template in `config.py`:
   ```python
   if 'new_account' in username.lower():
       return f"Custom caption for {username}\n{date_str}"
   ```

3. Add thread config (optional):
   ```bash
   TWITTER_THREAD_CONFIG={"new_account": {"anchor": "Custom anchor text"}}
   ```

### Add New Twitter Account

Not supported. Each repository uses a single Twitter account.

## Dependencies

**requests**: HTTP client for API calls
**tweepy**: Twitter API wrapper
**pillow**: Image processing and compression
**python-dotenv**: Environment variable loading from .env

All pinned in `requirements.txt`.

## Security Notes

- Never commit `.env` file (contains secrets)
- Use GitHub Secrets for API credentials in Actions
- Rotate API keys periodically
- Logs may contain URLs (media URLs are public anyway)

## For AI Agents

### Understanding the Codebase

1. **Start with main.py** - See CLI flags and flow
2. **Read story_archiver.py** - Core orchestration logic
3. **Check archive.json** - Understand data structure
4. **Review GitHub Actions** - See automation setup

### Making Changes

1. **Test locally** with `python main.py --fetch-only` first
2. **Check archive.json** to verify changes
3. **Test posting** with `python main.py --post-daily`
4. **Update docs** (README.md, QUICKSTART.md) if changing behavior

### Common Tasks

- **Add feature**: Add to story_archiver.py, expose via CLI flag
- **Fix bug**: Check logs, add error handling, test with test_setup.py
- **Update API**: Update respective API wrapper (instagram_api.py or twitter_api.py)
- **Change schedule**: Edit workflow YAML files

### Key Files to Know

- `main.py` - Entry point, CLI interface
- `story_archiver.py` - Core logic (most important)
- `archive_manager.py` - Database operations
- `config.py` - Configuration loading
- `.github/workflows/*.yml` - Automation
