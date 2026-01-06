# GitHub Actions Workflows

This directory contains three GitHub Actions workflows that automate the Instagram story archiving and posting process.

## Workflows

### `archive-stories.yml`

**Purpose**: Automatically fetch and archive Instagram stories every 8 hours

**Schedule**:
- Every 8 hours at minute 0 (cron: `0 */8 * * *` UTC)
- Manual trigger via "Run workflow" button

**What it does**:
1. Checks out the repository
2. Sets up Python 3.11
3. Installs dependencies
4. Runs the archiver in fetch-only mode: `python main.py --fetch-only`
5. Uploads logs as artifacts (7-day retention)
6. Commits and pushes archive updates to repository

**Key behavior**:
- Downloads and archives new stories from Instagram
- Saves media files to `media_cache/` directory
- Updates `archive.json` with story metadata
- Does NOT post to Twitter (handled by separate workflow)

### `post-stories.yml`

**Purpose**: Post yesterday's archived stories to Twitter at 00:00 UTC+7

**Schedule**:
- Daily at 00:00 UTC+7 (cron: `0 17 * * *` UTC - runs at 17:00 UTC previous day)
- Manual trigger via "Run workflow" button

**What it does**:
1. Checks out the repository
2. Sets up Python 3.11
3. Installs dependencies
4. Posts yesterday's stories: `python main.py --post-daily`
5. Uploads logs as artifacts (7-day retention)
6. Commits and pushes archive updates (with tweet_ids)

**Key behavior**:
- Groups stories by day (UTC+7 timezone)
- Posts stories where `uploadTime < today` (UTC+7)
- Batches up to 4 media items per tweet
- Updates `archive.json` with `tweet_ids`
- Deletes media files from `media_cache/` after successful posting

### `cleanup-media-cache.yml`

**Purpose**: Weekly comprehensive cleanup of media_cache directory

**Schedule**:
- Every Sunday at 02:00 UTC (09:00 UTC+7)
- Manual trigger via "Run workflow" button

**What it does**:
1. Checks out the repository
2. Sets up Python 3.11
3. Installs dependencies
4. Runs comprehensive media cache cleanup: `python main.py --cleanup-only`
5. Uploads logs as artifacts (7-day retention)
6. Commits and pushes any changes

**Key behavior**:
- Deletes media files for stories that have been successfully posted to Twitter
- Removes orphaned files that no longer correspond to any story in the archive
- Keeps files for stories that haven't been posted yet (including those planned for tomorrow)
- Provides additional cleanup beyond the automatic cleanup done after posting

## Workflow Separation

The three-workflow system provides better control and reliability:

1. **Archive workflow** (every 8 hours):
   - Focuses only on fetching new content
   - Runs frequently to catch new stories before they expire (24h on Instagram)
   - No Twitter posting to avoid rate limiting conflicts

2. **Post workflow** (daily at 00:00 UTC+7):
   - Processes all stories from the previous day in one batch
   - Ensures complete days are posted together
   - Organized threads with grouped media

3. **Cleanup workflow** (weekly on Sunday):
   - Performs comprehensive cleanup of media_cache directory
   - Removes files for successfully posted stories
   - Deletes orphaned files that no longer match archive entries
   - Runs as safety net beyond automatic cleanup after posting

## Environment

All workflows use:
- GitHub Secrets for API credentials (RAPIDAPI_KEY, TWITTER_*, etc.)
- GitHub Variables for non-secret config (INSTAGRAM_USERNAME, etc.)
- Ubuntu latest runner
- Python 3.11

## Setup

See [GITHUB_ACTIONS_SETUP.md](../GITHUB_ACTIONS_SETUP.md) for detailed setup instructions.

## Modifying Schedules

Edit the respective workflow file:

```yaml
on:
  schedule:
    - cron: '0 */8 * * *'  # Change this cron expression
```

### Current Schedules:
- Archive workflow: `0 */8 * * *` (every 8 hours)
- Post workflow: `0 17 * * *` (00:00 UTC+7 = 17:00 UTC previous day)
- Cleanup workflow: `0 2 * * 0` (Sunday 02:00 UTC = 09:00 UTC+7)

### Common examples:
- `0 * * * *` - Every hour
- `0 */2 * * *` - Every 2 hours
- `0 0 * * *` - Daily at midnight UTC
- `*/30 * * * *` - Every 30 minutes

**Important**: The post workflow schedule is relative to UTC. To run at 00:00 UTC+7, use `0 17 * * *` (17:00 UTC).

Reference: https://crontab.guru

## Troubleshooting

### Workflow didn't run
- Check if workflows are enabled in Settings
- Verify schedule is set correctly
- Check if branch is correct
- Note: Scheduled workflows may have delays (up to 1 hour)

### API authentication failed
- Verify secrets are set in Settings
- Ensure no extra spaces in secret values
- Check APIs haven't changed

### Git push failed
- Verify workflow has write permissions (Settings → Actions → Permissions)
- Check branch protection rules

### Stories not posting
- Check `archive.json` to see if stories have `tweet_ids` (already posted)
- Verify `taken_at` timestamps are from yesterday (UTC+7)
- Check logs for errors during posting

## Monitoring

### Check Workflow Runs
1. Go to **Actions** tab
2. Select workflow (Archive vs Post)
3. View recent runs and status

### View Logs
1. Click on a workflow run
2. Click on the job (archive or post)
3. Expand steps to see detailed logs

### Download Artifacts
1. Click on a completed workflow run
2. Scroll to "Artifacts" section
3. Download `archiver-logs` for full `archiver.log`

## Documentation

- Full setup: [GITHUB_ACTIONS_SETUP.md](../GITHUB_ACTIONS_SETUP.md)
- Main README: [../README.md](../README.md)
- Quick start: [../QUICKSTART.md](../QUICKSTART.md)
