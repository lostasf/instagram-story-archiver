# GitHub Actions Setup Guide

This project uses two GitHub Actions workflows for automated Instagram story archiving and posting.

## Overview

The archiver is orchestrated by two separate GitHub Actions workflows:

### Archive Workflow
- **Schedule**: Every 8 hours (cron: `0 */8 * * *` UTC)
- **Command**: `python main.py --fetch-only`
- **Purpose**: Fetch and archive new stories from Instagram
- **Runtime**: ~2-5 minutes per run
- **Does NOT post** to Twitter

### Post Workflow
- **Schedule**: Daily at 00:00 UTC+7 (cron: `0 17 * * *` UTC)
- **Command**: `python main.py --post-daily`
- **Purpose**: Post stories from previous days grouped by day
- **Runtime**: ~3-7 minutes per run
- **Posts** to Twitter with batched media

### Execution Environment
- **Runner**: Ubuntu latest
- **Storage**: Archive and logs committed back to repository
- **Cost**: Free for public repositories (2,000 minutes/month for private)

## Setup Instructions

### 1. Add Repository Secrets

Go to **Settings → Secrets and variables → Actions** and add the following secrets:

#### Instagram API (RapidAPI)
- `RAPIDAPI_KEY` - Your RapidAPI key
- `RAPIDAPI_HOST` - `instagram120.p.rapidapi.com` (or your API host)

#### Twitter API v2
- `TWITTER_API_KEY` - Consumer Key
- `TWITTER_API_SECRET` - Consumer Secret
- `TWITTER_ACCESS_TOKEN` - Access Token
- `TWITTER_ACCESS_SECRET` - Access Token Secret
- `TWITTER_BEARER_TOKEN` - Bearer Token

#### Discord Notifications (optional, recommended)
- `DISCORD_WEBHOOK_SUCCESS_URL` - Webhook URL for the success/info channel
- `DISCORD_WEBHOOK_FAILURE_URL` - Webhook URL for the failure/errors channel

### 2. Add Repository Variables

Go to **Settings → Secrets and variables → Variables** and add:

- `INSTAGRAM_USERNAME` - `jkt48.gendis` (single account) or `jkt48.gendis,jkt48.lana.a` (comma-separated list for multi-account)

**Tip**: Monitoring multiple accounts increases RapidAPI usage. Consider reducing the workflow schedule (e.g. every 2 hours) if you have a 1000/month quota.

**Optional advanced config**: If you want to use `INSTAGRAM_USERNAMES` / `TWITTER_THREAD_CONFIG` in GitHub Actions, add them to the workflow `env:` block in `.github/workflows/archive-stories.yml`.

**Note**: Variables are less sensitive than secrets and can be used for non-secret configuration.

### 3. Enable Workflow Permissions

Go to **Settings → Actions → General**:

- Ensure "Workflow permissions" is set to "Read and write permissions"
- Ensure "Allow GitHub Actions to create and approve pull requests" is disabled (optional)

### 4. First Run

The workflows will run automatically:
- **Archive workflow**: At the next scheduled 8-hour mark
- **Post workflow**: At 17:00 UTC (00:00 UTC+7)

You can also manually trigger them via "Run workflow".

## Manual Triggers

### Run Archive Workflow

1. Go to **Actions** tab
2. Select "Archive Instagram Stories" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

### Run Post Workflow

1. Go to **Actions** tab
2. Select "Post Instagram Stories" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

### View Execution

1. Go to **Actions** tab
2. Click on the latest run
3. Click on the job to see detailed logs

## Workflow Details

### Cron Expressions

**Archive workflow** (`archive-stories.yml`):
```yaml
cron: '0 */8 * * *'  # Every 8 hours
```

**Post workflow** (`post-stories.yml`):
```yaml
cron: '0 17 * * *'  # Daily at 00:00 UTC+7 (17:00 UTC previous day)
```

### Modifying Schedules

Edit the respective workflow file:

```yaml
on:
  schedule:
    - cron: '0 */8 * * *'  # Change this cron expression
```

**Common examples**:
- `0 * * * *` - Every hour
- `0 */2 * * *` - Every 2 hours
- `0 0 * * *` - Daily at midnight UTC
- `0 17 * * *` - Daily at 17:00 UTC (00:00 UTC+7)
- `*/30 * * * *` - Every 30 minutes

**Important**: The post workflow schedule is relative to UTC. To run at 00:00 UTC+7, use `0 17 * * *` (17:00 UTC).

Reference: https://crontab.guru

### What the Archive Workflow Does

1. **Checkout** - Clones the repository
2. **Setup Python** - Installs Python 3.11
3. **Install Dependencies** - Runs `pip install -r requirements.txt`
4. **Archive Stories** - Runs `python main.py --fetch-only`
   - Fetches new stories from Instagram
   - Downloads media to `media_cache/`
   - Updates `archive.json` with story metadata
   - Does NOT post to Twitter
5. **Upload Logs** - Saves logs as artifacts (7-day retention)
6. **Commit Changes** - Commits updated `archive.json` and `archiver.log`
7. **Push** - Pushes changes back to repository

### What the Post Workflow Does

1. **Checkout** - Clones the repository
2. **Setup Python** - Installs Python 3.11
3. **Install Dependencies** - Runs `pip install -r requirements.txt`
4. **Post Stories** - Runs `python main.py --post-daily`
   - Groups stories from previous days by day (UTC+7)
   - Posts to Twitter with up to 4 media items per tweet
   - Updates `archive.json` with `tweet_ids`
   - Deletes media files from `media_cache/`
5. **Upload Logs** - Saves logs as artifacts (7-day retention)
6. **Commit Changes** - Commits updated `archive.json` and `archiver.log`
7. **Push** - Pushes changes back to repository

### Security

- ✅ Secrets are masked in logs
- ✅ Only repository maintainers can modify secrets
- ✅ Workflow runs in isolated Ubuntu container
- ✅ No local machine access needed
- ✅ Archive tracked in git history

### Environment Variables

Passed to the workflow:

```yaml
RAPIDAPI_KEY: ${{ secrets.RAPIDAPI_KEY }}
TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
# ... other credentials from secrets
INSTAGRAM_USERNAME: ${{ vars.INSTAGRAM_USERNAME }}
```

## Monitoring

### Check Status

1. **Actions Tab** - See all workflow runs
2. **Badges** - Add to README:
   ```markdown
   ![Archive Stories](https://github.com/username/repo/actions/workflows/archive-stories.yml/badge.svg)
   ```

### View Logs

1. **During Run** - Watch in real-time
2. **After Run** - Click run to see full logs
3. **Artifacts** - Download `archiver-logs` for full `archiver.log`

### Troubleshooting

#### Workflow didn't run

- Check **Actions** tab for disabled workflows
- Verify schedule time (runs at top of hour UTC)
- Check repository isn't archived
- Verify branch is set correctly

#### API Authentication Failed

- Verify all secrets are set correctly (copy-paste carefully)
- No extra spaces or quotes in secrets
- Check APIs haven't changed endpoints

#### Git Push Failed

- Verify workflow has write permissions (Settings → Actions → Permissions)
- Check branch protection rules don't block commits

#### Out of Quota

- Check RapidAPI remaining requests
- Verify Twitter API rate limits
- Consider increasing cron interval

### View Run History

Each run creates an entry in the git history:

```bash
git log --oneline | head -20
```

Example:
```
abc1234 chore: update archive and logs [skip ci]
def5678 chore: update archive and logs [skip ci]
ghi9012 Initial commit
```

## Cost Considerations

### Public Repository

- **Cost**: Free
- **Minutes**: Unlimited
- **Runs**: Unlimited

### Private Repository

- **Cost**: Included in GitHub
- **Minutes**: 2,000 free per month
- **Calculation**:
  - Archive workflow: ~5 min × 3 runs/day × 30 days = 450 min/month
  - Post workflow: ~5 min × 1 run/day × 30 days = 150 min/month
  - **Total**: ~600 min/month (well under 2,000 limit)

If you need to reduce usage:

1. **Increase archive interval**:
    ```yaml
    cron: '0 */12 * * *'  # Every 12 hours = 60 runs/month = 300 min
    ```

2. **Upgrade plan** for more GitHub Actions minutes

## Advanced Configuration

### Conditional Execution

Both workflows already have built-in conditional logic:
- Archive workflow: Only processes new stories
- Post workflow: Only posts stories from previous days (UTC+7)

### Notifications

Add Slack/Discord notifications on failure:

Add to either workflow:

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Archive story failed!'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Maintenance

### Update Dependencies

Periodically update Python packages:

```bash
# Update requirements.txt
pip install --upgrade requests tweepy pillow python-dotenv
pip freeze > requirements.txt
```

### Monitor Logs

Periodically review logs for errors:

1. Go to **Actions**
2. Click workflow run
3. Download `archiver-logs` artifact
4. Review `archiver.log`

### Archive Growth

The `archive.json` file grows over time. GitHub has size limits for individual files, but JSON archives typically remain manageable for years of use.

## Disabling Workflows

### Temporarily

1. Go to **Actions**
2. Click workflow name
3. Click "..." menu
4. Select "Disable workflow"

### Permanently

1. Delete `.github/workflows/archive-stories.yml` or `.github/workflows/post-stories.yml`
2. Commit and push

## Example Deployment

### Fork and Deploy

1. **Fork repository** on GitHub
2. **Go to Settings → Secrets and variables → Actions**
3. **Add all required secrets and variables**
4. **Wait for next scheduled run** or manually trigger
5. **Check Actions tab** for results

### Expected Results

- **Archive workflow**: Runs every 8 hours, downloads new stories
- **Post workflow**: Runs daily at 00:00 UTC+7, posts stories from previous days
- `archive.json` tracks all archived stories with timestamps
- `archiver.log` available in artifacts (7-day retention)

## FAQ

### Q: How much does it cost?

**A**: Free for public repos. Private repos get 2,000 free minutes/month (~600 min/month used, well under limit).

### Q: Can I change the schedule?

**A**: Yes, edit the respective workflow file and change the cron expression. Remember: post workflow is relative to UTC, so `0 17 * * *` = 00:00 UTC+7.

### Q: What if the workflow fails?

**A**: GitHub sends notifications. Download logs from artifacts to debug. Common issues: expired API keys, rate limits, network errors.

### Q: Can I manually trigger runs?

**A**: Yes, use "Run workflow" in Actions tab anytime. Choose between Archive and Post workflows.

### Q: Will logs persist?

**A**: Logs are committed to git and kept 7 days as artifacts.

### Q: Do I need to pay for GitHub Actions?

**A**: Free for public repos. Private repos get 2,000 free minutes/month.

### Q: Why two separate workflows?

**A**: Separation provides better control:
- Archive workflow runs frequently to catch new stories before they expire (24h on Instagram)
- Post workflow runs once daily to post complete days in organized threads
- Avoids rate limiting conflicts between fetching and posting

### Q: What if I post stories manually?

**A**: Manually posted stories will be tracked in `archive.json` with `tweet_ids`. The post workflow will skip stories that already have `tweet_ids`.

### Q: Can I skip the post workflow?

**A**: Yes, disable or delete `.github/workflows/post-stories.yml`. Stories will still be archived but won't be posted automatically.

### Q: What if credentials change?

**A**: Update secrets in Settings → Secrets and variables → Actions

## Support

- 📖 GitHub Actions Docs: https://docs.github.com/en/actions
- 🐛 Debug failed runs: Check Actions → Run → Job logs
- 💬 Cron syntax: https://crontab.guru
- 📚 Full documentation: See [README.md](README.md)

---

Your archiver is now running automatically on GitHub! 🚀
