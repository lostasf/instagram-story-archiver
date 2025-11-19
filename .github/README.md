# GitHub Actions Workflows

This directory contains GitHub Actions workflows that automate the Instagram story archiving process.

## Workflows

### `archive-stories.yml`

**Purpose**: Automatically archive Instagram stories every hour

**Trigger**: 
- Every hour at minute 0 (`0 * * * *`)
- Manual trigger via "Run workflow" button

**What it does**:
1. Checks out the repository
2. Sets up Python 3.11
3. Installs dependencies
4. Runs the archiver (`python main.py`)
5. Uploads logs as artifacts
6. Commits and pushes archive updates

**Environment**:
- Uses GitHub Secrets for API credentials
- Uses GitHub Variables for non-secret config
- Runs on Ubuntu latest

**Cost**:
- Free for public repositories
- 2,000 free minutes/month for private repos

## Setup

See [GITHUB_ACTIONS_SETUP.md](../GITHUB_ACTIONS_SETUP.md) for detailed setup instructions.

## Modifying Schedules

Edit `.github/workflows/archive-stories.yml`:

```yaml
on:
  schedule:
    - cron: '0 * * * *'  # Change this cron expression
```

Common examples:
- `0 * * * *` - Every hour
- `0 */2 * * *` - Every 2 hours
- `0 0 * * *` - Daily at midnight UTC
- `*/30 * * * *` - Every 30 minutes

Reference: https://crontab.guru

## Troubleshooting

### Workflow didn't run

- Check if workflows are enabled in Settings
- Verify schedule is set correctly
- Check if branch is correct

### API authentication failed

- Verify secrets are set in Settings
- Ensure no extra spaces in secret values
- Check APIs haven't changed

### Git push failed

- Verify workflow has write permissions
- Check branch protection rules

## Documentation

- Full setup: [GITHUB_ACTIONS_SETUP.md](../GITHUB_ACTIONS_SETUP.md)
- Main README: [../README.md](../README.md)
- Quick start: [../QUICKSTART.md](../QUICKSTART.md)
