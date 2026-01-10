# Quick Guide for AI Agents

This document helps AI agents quickly understand and work with this codebase.

## TL;DR Architecture

**Purpose**: Archive Instagram stories and post them to Twitter/X with automated GitHub Actions workflows.

**Core Flow**:
1. Archive workflow (every 8h): Downloads stories from Instagram → saves to `archive.json`
2. Post workflow (daily at 00:00 UTC+7): Groups stories from previous days → posts to Twitter in threads
3. Cleanup workflow (weekly): Cleans up media cache and maintains repository

**Key Components**:
- `main.py` - Entry point with CLI flags
- `story_archiver.py` - Core orchestration (most important)
- `archive_manager.py` - JSON database operations
- `instagram_api.py` - Instagram API wrapper (RapidAPI)
- `twitter_api.py` - Twitter API wrapper (v2)
- `media_manager.py` - Media download and compression
- `config.py` - Configuration from environment variables

## Critical Concepts

### Three-Workflow System

**Archive workflow** (`.github/workflows/archive-stories.yml`):
- Runs every 8 hours: `cron: '0 */8 * * *'` (UTC)
- Command: `python main.py --fetch-only`
- Purpose: Fetch and archive new stories
- Does NOT post to Twitter

**Post workflow** (`.github/workflows/post-stories.yml`):
- Runs daily at 00:00 UTC+7: `cron: '0 17 * * *'` (UTC)
- Command: `python main.py --post-daily`
- Purpose: Post stories from previous days grouped by day
- Posts to Twitter with batched media

**Cleanup workflow** (`.github/workflows/cleanup-media-cache.yml`):
- Runs weekly on Sundays at 02:00 UTC (09:00 UTC+7)
- Command: `python main.py --archive-only --cleanup-only`
- Purpose: Clean up media cache and push repository changes
- Commits all file changes including deletions using `git add -A`

### Post Flow (Robustness)

**Critical Error Handling**:
- If posting fails partway (e.g., Twitter rate limit), the script MUST:
  1. Update `archive.json` with successful `tweet_ids` (done automatically during posting).
  2. Clean up media cache for successful posts.
  3. **Commit and push** the updated `archive.json` and `archiver.log` to the repository.
  4. Only then return an error code 1.
- This ensures the next run picks up exactly where it left off.
- Implementation: `archiver.commit_and_push_to_repo()` in `main.py`.

### Timezone Logic (CRITICAL)

All posting logic uses **UTC+7 timezone**:
- Instagram's `taken_at` is Unix timestamp (UTC)
- Convert to UTC+7 to determine "previous days"
- Stories where `taken_at < today (UTC+7)` are eligible for posting
- Stories uploaded today (UTC+7) are NOT posted until tomorrow

Example:
- Story uploaded at 2024-01-15 23:00 UTC = 2024-01-16 06:00 UTC+7
- If today (UTC+7) is 2024-01-16, this story will NOT post (same day)
- Will post tomorrow when today becomes 2024-01-17 (UTC+7)

### Archive Database (`archive.json`)

**Schema**:
```json
{
  "schema_version": 2,
  "accounts": {
    "username": {
      "anchor_tweet_id": "...",
      "last_tweet_id": "...",
      "last_check": "...",
      "archived_stories": [
        {
          "story_id": "...",
          "taken_at": 1705305600,  // Unix timestamp (UTC) - KEY FIELD
          "tweet_ids": [],  // Empty = not posted yet
          "local_media_paths": ["..."],  // Downloaded media files
          "media_types": ["image", "video"],
          "media_count": 3
        }
      ]
    }
  }
}
```

**Key fields**:
- `taken_at`: Unix timestamp from Instagram API (UTC) - determines posting eligibility
- `tweet_ids`: Array of tweet IDs (empty = not posted)
- `local_media_paths`: Array of downloaded media file paths
- `media_types`: Array of media types ("image" or "video")

### Multi-Media Batching

Twitter allows up to 4 media items per tweet (images or videos).

**Posting flow**:
1. Group stories by day (using `taken_at` in UTC+7)
2. For each day:
   - Create/reply to anchor tweet
   - Batch up to 4 media items per tweet
   - Post tweets with progress indicators: `(1/2)`, `(2/2)`

## CLI Flags

| Flag | Purpose | Workflow |
|------|---------|-----------|
| `--fetch-only` | Archive only, no posting | Archive workflow |
| `--post-daily` | Post stories from previous days grouped by day | Post workflow |
| `--status` | Show archive statistics | Both (monitoring) |
| `--story-id` | Archive specific story | Testing/debugging |
| `--username` | Specify Instagram username | With --story-id |
| `--verify-twitter` | Verify Twitter API credentials | Troubleshooting |
| `--cleanup-only` | Run media cache cleanup only | Cleanup workflow |
| `--archive-only` | Archive stories without posting | Alias for --fetch-only |

## GitHub Actions

**Files**:
- `.github/workflows/archive-stories.yml` - Archive workflow
- `.github/workflows/post-stories.yml` - Post workflow
- `.github/workflows/cleanup-media-cache.yml` - Cleanup workflow
- `.github/README.md` - Workflow documentation

**Schedules**:
- Archive: `0 */8 * * *` (every 8 hours UTC)
- Post: `0 17 * * *` (00:00 UTC+7 = 17:00 UTC previous day)
- Cleanup: `0 2 * * 0` (Sundays at 02:00 UTC = 09:00 UTC+7)

## Common Tasks

### Test Locally

```bash
# Test configuration and API connections
python test_setup.py

# Archive only (no posting)
python main.py --fetch-only

# Post stories from previous days
python main.py --post-daily

# Check archive status
python main.py --status
```

### Debug Posting Issues

```bash
# Check what would be posted
python main.py --status

# View archive as JSON
python -m json.tool archive.json

# Count unposted stories
python -c "import json; data=json.load(open('archive.json')); print(sum(1 for s in data['accounts']['jkt48.gendis']['archived_stories'] if not s['tweet_ids']))"
```

### Change Schedule

Edit respective workflow file:
```yaml
on:
  schedule:
    - cron: '0 17 * * *'  # Change this expression
```

**Remember**: Post workflow is relative to UTC. To run at 00:00 UTC+7, use `0 17 * * *` (17:00 UTC).

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

## Key Files to Edit

**For logic changes**:
- `story_archiver.py` - Core archiving and posting logic
- `config.py` - Configuration and caption templates

**For schedule changes**:
- `.github/workflows/archive-stories.yml` - Archive schedule
- `.github/workflows/post-stories.yml` - Post schedule

**For documentation updates**:
- `README.md` - Main documentation
- `QUICKSTART.md` - Quick start guide
- `GITHUB_ACTIONS_SETUP.md` - GitHub Actions setup
- `DEVELOPER_NOTES.md` - Technical documentation (for developers)

## Important Gotchas

1. **UTC+7 Timezone**: All posting logic uses UTC+7, not UTC or local time
2. **Same-Day Stories**: Stories uploaded today (UTC+7) won't post until tomorrow
3. **Media Cleanup**: Media files are deleted from `media_cache/` after successful posting
4. **Workflow Separation**: Archive workflow does NOT post, Post workflow does NOT fetch
5. **Git Commits**: Both workflows commit changes to `archive.json` after running

## Dependencies

- `requests` - HTTP client for API calls
- `tweepy` - Twitter API wrapper
- `pillow` - Image processing and compression
- `python-dotenv` - Environment variable loading

All pinned in `requirements.txt`.

## Testing

**No formal unit tests yet.** Use manual testing:

```bash
# Test all configurations and API connections
python test_setup.py

# Test Twitter OAuth specifically
python diagnose_twitter_oauth.py

# Archive specific story
python main.py --story-id <story_id> --username <username>
```

## Documentation Structure

- `README.md` - Main documentation (features, setup, troubleshooting)
- `QUICKSTART.md` - Get running in 3 minutes
- `GITHUB_ACTIONS_SETUP.md` - Complete GitHub Actions setup
- `DEVELOPER_NOTES.md` - Technical reference (architecture, code details)
- `.github/README.md` - Workflow-specific documentation
- `TWITTER_OAUTH_FIX_GUIDE.md` - Twitter OAuth troubleshooting (comprehensive)
- `AI_AGENT_GUIDE.md` - This document (for AI agents)
- `DISCORD_SETUP.md` - Discord webhook integration setup

## Common Errors

### "No stories to post"
- Normal if all stories have already been posted
- Check `archive.json` for `tweet_ids` (empty = not posted)
- Check `taken_at` timestamps - stories from today (UTC+7) won't post until tomorrow

### "Rate limit exceeded"
- Increase archive workflow interval
- Verify RapidAPI subscription is active
- Check remaining quota at https://rapidapi.com/dashboard

### "403 Forbidden - OAuth1 app permissions"
- Twitter app permissions must be "Read and Write"
- Regenerate Access Token and Secret after changing permissions
- See `TWITTER_OAUTH_FIX_GUIDE.md` for detailed fix instructions
- Use `python main.py --verify-twitter` to test credentials

## Making Changes

1. **Read the code** - Start with `story_archiver.py` for logic, `archive_manager.py` for data structure
2. **Test locally** - Use `python main.py --fetch-only` first
3. **Check archive** - Verify `archive.json` changes
4. **Test posting** - Use `python main.py --post-daily`
5. **Update docs** - Update relevant documentation if behavior changes

## Questions?

Check the full documentation:
- `README.md` - Comprehensive documentation
- `DEVELOPER_NOTES.md` - Technical details and architecture
- `GITHUB_ACTIONS_SETUP.md` - GitHub Actions setup and configuration
