# GitHub Actions Setup Guide

This project is configured to run automatically every 1 hour using GitHub Actions.

## Overview

Instead of running a local scheduler, the archiver is orchestrated by GitHub Actions:

- **Trigger**: Every 1 hour (cron: `0 * * * *`)
- **Execution**: Ubuntu latest runner
- **Runtime**: ~2-5 minutes per run
- **Storage**: Archive and logs committed back to repository
- **Cost**: Free for public repositories (1,000 minutes/month for private)

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

### 2. Add Repository Variables

Go to **Settings → Secrets and variables → Variables** and add:

- `INSTAGRAM_USERNAME` - `jkt48.gendis` (or target account)

**Note**: Variables are less sensitive than secrets and can be used for non-secret configuration.

### 3. Enable Workflow Permissions

Go to **Settings → Actions → General**:

- Ensure "Workflow permissions" is set to "Read and write permissions"
- Ensure "Allow GitHub Actions to create and approve pull requests" is disabled (optional)

### 4. First Run

The workflow will run automatically:
- At the next top of the hour
- When you manually trigger it via "Run workflow"

## Manual Triggers

### Run Now

1. Go to **Actions** tab
2. Select "Archive Instagram Stories" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

### View Execution

1. Go to **Actions** tab
2. Click on the latest run
3. Click "archive" job to see logs

## Workflow Details

### Cron Expression

```
0 * * * *
└─ runs at minute 0 of every hour
```

To modify the schedule, edit `.github/workflows/archive-stories.yml`:

```yaml
on:
  schedule:
    - cron: '0 * * * *'  # Every hour
    # Examples:
    # - cron: '0 */2 * * *'  # Every 2 hours
    # - cron: '0 0 * * *'    # Daily at midnight UTC
    # - cron: '*/30 * * * *'  # Every 30 minutes
```

### What the Workflow Does

1. **Checkout** - Clones the repository
2. **Setup Python** - Installs Python 3.11
3. **Install Dependencies** - Runs `pip install -r requirements.txt`
4. **Archive Stories** - Runs `python main.py` with API credentials
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
- **Calculation**: 24 hours × 30 days = 720 runs × 5 min = 3,600 minutes
- **Note**: This exceeds free tier - consider adjusting schedule

**Options for private repos:**

1. **Increase interval** to reduce runs:
   ```yaml
   cron: '0 */4 * * *'  # Every 4 hours = 180 runs/month = 900 minutes
   ```

2. **Set limits** on story processing to reduce execution time

3. **Upgrade plan** for more GitHub Actions minutes

## Advanced Configuration

### Conditional Execution

Only run if stories exist:

Edit `.github/workflows/archive-stories.yml`:

```yaml
- name: Archive Instagram stories
  env:
    # ... environment variables
  run: |
    python main.py
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
      echo "Archive failed with exit code $EXIT_CODE"
      exit $EXIT_CODE
    fi
```

### Multiple Schedules

Run at different times:

```yaml
on:
  schedule:
    - cron: '0 8 * * *'   # 8 AM UTC
    - cron: '0 20 * * *'  # 8 PM UTC
```

### Notifications

Add Slack/Discord notifications on failure:

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
pip install --upgrade requests tweepy pillow
pip freeze > requirements.txt
```

### Archive Cleanup

Archive database grows over time:

```bash
# Manual cleanup (keep last 1000 stories)
# This would be a separate workflow or local script
```

### Monitor Logs

Periodically review logs for errors:

1. Go to **Actions**
2. Click workflow run
3. Download `archiver-logs` artifact
4. Review `archiver.log`

## Disabling Workflow

### Temporarily

1. Go to **Actions**
2. Click workflow name
3. Click "..." menu
4. Select "Disable workflow"

### Permanently

1. Delete `.github/workflows/archive-stories.yml`
2. Commit and push

## Re-enabling Local Scheduling (Optional)

If you want to switch back to local scheduling:

1. Edit `main.py` to restore `ArchiverScheduler` class
2. Re-add `schedule==1.2.0` to `requirements.txt`
3. Run `python main.py` locally
4. Disable GitHub Actions workflow

## Example Deployment

### Fork and Deploy

1. **Fork repository** on GitHub
2. **Go to Settings → Secrets and variables → Actions**
3. **Add all required secrets**
4. **Wait for next hour** or manually trigger
5. **Check Actions tab** for results

### Results

- Archive automatically updates every hour
- Stories posted to Twitter in threads
- `archive.json` tracks what's archived
- `archiver.log` available in artifacts

## FAQ

### Q: How much does it cost?

**A**: Free for public repos. Private repos get 2,000 free minutes/month (enough for ~40 runs at 5 min each, or daily runs).

### Q: Can I change the schedule?

**A**: Yes, edit `.github/workflows/archive-stories.yml` and change the cron expression.

### Q: What if the workflow fails?

**A**: GitHub sends notifications. Download logs from artifacts to debug.

### Q: Can I manually trigger runs?

**A**: Yes, use "Run workflow" in Actions tab anytime.

### Q: Will logs persist?

**A**: Logs are committed to git and kept 7 days as artifacts.

### Q: Do I need to pay for GitHub Actions?

**A**: Free for public repos. Private repos get 2,000 free minutes/month.

### Q: Can I run multiple workflows?

**A**: Yes, create more `.yml` files in `.github/workflows/` for other tasks.

### Q: What if credentials change?

**A**: Update secrets in Settings → Secrets and variables → Actions

## Support

- 📖 GitHub Actions Docs: https://docs.github.com/en/actions
- 🐛 Debug failed runs: Check Actions → Run → Job logs
- 💬 Cron syntax: https://crontab.guru

---

Your archiver is now running automatically on GitHub! 🚀
