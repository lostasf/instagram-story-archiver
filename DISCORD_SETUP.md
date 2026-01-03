# Discord Webhook Setup Guide

This guide will help you set up Discord notifications for your Instagram Story Archiver bot.

## What Gets Notified

Your Discord webhook will receive notifications for:

🚀 **GitHub Actions**
- Workflow starts (archive and post workflows)
- Successful runs:
  - **Fetch-only**: per-account story counts (fetched / new archived / already posted)
  - **Post-daily**: per-account counts (new stories posted / total archived)
- Failed runs (traceback + recent logs)

📸 **Instagram API**
- Failed fetch attempts (HTTP status + response)

🐦 **Twitter API**
- Posting failures (HTTP status + response) — includes 403/401 and other errors

## Setup Instructions

### 1. Create 2 Discord Webhooks (recommended)

Create two channels (or reuse existing ones):
- **Success / info** channel (clean summaries)
- **Failure / errors** channel (HTTP codes + responses)

Then create 2 webhooks:

1. Open Discord and go to your server
2. Go to **Server Settings** → **Integrations**
3. Click **Webhooks** → **New Webhook**
4. Create a webhook for your **success** channel → copy its URL
5. Create a webhook for your **failure** channel → copy its URL

### 2. Add Webhooks to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:
   - `DISCORD_WEBHOOK_SUCCESS_URL` (success/info channel webhook)
   - `DISCORD_WEBHOOK_FAILURE_URL` (failure/errors channel webhook)

> Legacy fallback: you can still use `DISCORD_WEBHOOK_URL` (single channel), but split webhooks are recommended.

### 3. (Optional) Local Development

If you want Discord notifications during local testing:

1. Copy `.env.example` to `.env`
2. Add your webhook URLs:
   ```bash
   DISCORD_WEBHOOK_SUCCESS_URL=https://discord.com/api/webhooks/your-success-webhook-url
   DISCORD_WEBHOOK_FAILURE_URL=https://discord.com/api/webhooks/your-failure-webhook-url
   ```

## Webhook URL Format

Your Discord webhook URL should look like:
```
https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz
```

## Test Your Setup

To verify it's working:

1. Trigger a manual GitHub Actions run:
   - Go to **Actions** tab in your repository
   - Select a workflow (Archive or Post)
   - Click **Run workflow**

2. Check your Discord channel for notifications

3. You should see:
   - 🚀 Start notification when workflow begins
   - ✅ Success notification with logs when complete
   - Or ❌ Failure notification with error details if something went wrong

## Troubleshooting

### No Discord notifications?

1. **Check webhook URL format**
   - Ensure the URL is complete and starts with `https://`
   - No extra spaces or characters

2. **Verify GitHub secrets**
   - Recommended: set both `DISCORD_WEBHOOK_SUCCESS_URL` and `DISCORD_WEBHOOK_FAILURE_URL`
   - No typos in the webhook URLs
   - Legacy: `DISCORD_WEBHOOK_URL` (single channel) is still supported

3. **Check workflow files**
   - Ensure `.github/workflows/*.yml` files include:
     - `DISCORD_WEBHOOK_SUCCESS_URL`
     - `DISCORD_WEBHOOK_FAILURE_URL`

4. **Enable for local development**
   - Make sure `.env` file exists with the webhook URLs
   - Verify `DISCORD_WEBHOOK_SUCCESS_URL` and `DISCORD_WEBHOOK_FAILURE_URL` are set in your environment

### Notifications work for GitHub Actions but not local runs?

- Local notifications work if `DISCORD_WEBHOOK_SUCCESS_URL` / `DISCORD_WEBHOOK_FAILURE_URL` are set in your `.env` file
- GitHub Actions notifications work automatically when the secrets are configured

### Want to disable notifications?

Simply remove or leave blank the Discord webhook secrets (or env vars). The bot will continue to work normally but won't send Discord notifications.

## Notification Examples

### Success Notification
```
✅ GitHub Action Success
Workflow: Post Instagram Stories completed successfully.
[Recent logs shown here]
```

### Error Notification
```
❌ GitHub Action Failed
Workflow: Archive Instagram Stories failed with error:
[Error traceback shown here]
**Recent logs:**
[Log excerpt shown here]
```

### Instagram API Error
```
⚠️ Instagram Stories Fetch Failed
Failed to fetch stories from @username
Error: RequestException details...
**Response Data:**
[API response shown here]
```

### Twitter 403 Error
```
❌ Twitter Post Failed
Failed to post stories from @username to Twitter
**⚠️ Authorization Error (403)** - Check Twitter API permissions!
**Response:**
[Twitter API error response]
```

## Security Notes

- Discord webhook URLs are sensitive - treat them like passwords
- Never commit webhook URLs to git repositories
- Always use GitHub Secrets for webhook URLs in workflows
- Consider rotating your webhook URL periodically for security

## Additional Resources

- [Discord Webhooks Guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [Instagram Story Archiver README](README.md)