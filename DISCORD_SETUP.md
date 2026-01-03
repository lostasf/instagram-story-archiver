# Discord Webhook Setup Guide

This guide will help you set up Discord notifications for your Instagram Story Archiver bot.

## What Gets Notified

Your Discord webhook will receive notifications for:

🚀 **GitHub Actions**
- Workflow starts (archive and post workflows)
- Successful runs (with log summaries)
- Failed runs (with full error traces and logs)

📸 **Instagram API**
- Successful story fetches (with story count)
- Failed fetch attempts (with error responses)

🐦 **Twitter API**
- Successful story posts (with tweet links)
- 403 Permission errors (detailed troubleshooting info)
- Other API errors (with full response data)

## Setup Instructions

### 1. Create Discord Webhook

1. Open Discord and go to your server
2. Go to **Server Settings** → **Integrations**
3. Click **Webhooks** → **New Webhook**
4. Choose a name (e.g., "Story Archiver Bot")
5. Select the channel where you want notifications
6. Click **Copy Webhook URL**

### 2. Add Webhook to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `DISCORD_WEBHOOK_URL`
5. Value: Paste your Discord webhook URL
6. Click **Add secret**

### 3. (Optional) Local Development

If you want Discord notifications during local testing:

1. Copy `.env.example` to `.env`
2. Add your webhook URL:
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url
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

2. **Verify GitHub secret**
   - Secret name must be exactly `DISCORD_WEBHOOK_URL`
   - No typos in the webhook URL

3. **Check workflow files**
   - Ensure `.github/workflows/*.yml` files include `DISCORD_WEBHOOK_URL` in the `env` section
   - Both `archive-stories.yml` and `post-stories.yml` should have it

4. **Enable for local development**
   - Make sure `.env` file exists with the webhook URL
   - Verify `DISCORD_WEBHOOK_URL` is set in your environment

### Notifications work for GitHub Actions but not local runs?

- Local notifications only work if `DISCORD_WEBHOOK_URL` is set in your `.env` file
- GitHub Actions notifications work automatically when the secret is configured

### Want to disable notifications?

Simply remove or leave blank the `DISCORD_WEBHOOK_URL` in your `.env` file or GitHub secrets. The bot will continue to work normally but won't send Discord notifications.

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