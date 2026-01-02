# Twitter OAuth Permissions Fix Guide

## Problem: 403 Forbidden Error

If you're seeing this error:
```
Twitter API Permission Error (403 Forbidden)
```

This means your Twitter app does not have write permissions.

## Root Cause

Twitter requires specific permissions to post tweets and upload media. The error occurs when:
1. Your Twitter app permissions are set to "Read" instead of "Read and Write"
2. You changed permissions but didn't regenerate your Access Token and Secret
3. The OAuth 1.0a settings are not configured correctly

## Solution: Fix Twitter App Permissions

### Step 1: Go to Twitter Developer Portal

Visit: https://developer.twitter.com/en/portal/dashboard

### Step 2: Select Your App

Click on the app you're using for this project.

### Step 3: Change App Permissions

1. Go to **Settings** > **App permissions**
2. Change from "Read" to **"Read and Write"**
3. Click "Save"

### Step 4: Configure OAuth 1.0a

1. Go to **Settings** > **User authentication settings**
2. Make sure OAuth 1.0a is enabled
3. Set **App permissions** to "Read and Write"
4. Set **Type of App** to "Web App, Automated App or Bot"
5. Set **Callback URI / Website** to any valid URL (e.g., `https://example.com/callback`)
6. Set **Website URL** to any valid URL (e.g., `https://example.com`)
7. Click "Save"

### Step 5: REGENERATE ACCESS TOKENS (CRITICAL!)

⚠️ **This is the most important step!** ⚠️

After changing permissions, you MUST regenerate your Access Token and Secret:

1. Go to **Settings** > **Keys and tokens**
2. Scroll to **Authentication Tokens** > **OAuth 1.0a**
3. Click **"Regenerate"** next to **Access Token and Secret**
4. Copy the new **Access Token** and **Access Token Secret**
5. Click **"Regenerate"** next to **Bearer Token** (optional, but recommended)
6. Copy the new **Bearer Token**

**THE OLD TOKENS WILL NOT WORK WITH THE NEW PERMISSIONS!**

### Step 6: Update GitHub Actions Secrets

Update these secrets in your GitHub repository:

```
TWITTER_ACCESS_TOKEN=<new_access_token>
TWITTER_ACCESS_SECRET=<new_access_secret>
TWITTER_BEARER_TOKEN=<new_bearer_token>
```

Keep these unchanged:
- `TWITTER_API_KEY` (Consumer Key)
- `TWITTER_API_SECRET` (Consumer Secret)

## How to Verify the Fix

### Option 1: Run the Verification Command

```bash
python main.py --verify-twitter
```

This will check if your credentials are valid and have the correct permissions.

If successful, you'll see:
```
✓ Twitter API credentials are valid
✓ Your Twitter app has the correct permissions
```

If there's still an issue, it will show detailed error messages.

### Option 2: Test Locally

1. Create a `.env` file with your credentials:
```bash
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_new_access_token
TWITTER_ACCESS_SECRET=your_new_access_secret
TWITTER_BEARER_TOKEN=your_new_bearer_token
```

2. Run the verification:
```bash
python main.py --verify-twitter
```

## Common Mistakes

### ❌ Mistake 1: Not regenerating tokens after changing permissions
- **Problem**: Old tokens are tied to old permissions
- **Solution**: Always regenerate tokens after changing permissions

### ❌ Mistake 2: Only changing v2 API permissions
- **Problem**: Media upload uses v1.1 API (OAuth 1.0a)
- **Solution**: Ensure OAuth 1.0a is also set to "Read and Write"

### ❌ Mistake 3: Not updating GitHub Actions secrets
- **Problem**: GitHub still uses old tokens
- **Solution**: Update all affected secrets after regenerating tokens

### ❌ Mistake 4: Using OAuth 2.0 only
- **Problem**: Media upload requires OAuth 1.0a
- **Solution**: Use both OAuth 1.0a tokens (for media) and OAuth 2.0 (for posting)

## Understanding the Twitter API Architecture

This project uses two different Twitter API approaches:

1. **OAuth 1.0a (v1.1 API)** - Used for media upload
   - Requires: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`
   - Used by: `twitter_api.v1_client.media_upload()`

2. **OAuth 2.0 (v2 API)** - Used for posting tweets
   - Requires: `TWITTER_BEARER_TOKEN` and/or OAuth 1.0a credentials
   - Used by: `twitter_api.client.create_tweet()`

Both need "Read and Write" permissions to work correctly.

## Troubleshooting Commands

### Check current configuration
```bash
python main.py --status
```

### Verify Twitter credentials
```bash
python main.py --verify-twitter
```

### Test with a specific story (won't post)
```bash
python main.py --fetch-only
```

## Still Having Issues?

1. **Check the logs**: Look at `archiver.log` for detailed error messages
2. **Verify all secrets**: Make sure all 5 Twitter secrets are set correctly
3. **Try a manual test**: Use Twitter's API explorer to test your credentials
4. **Check rate limits**: You might be hitting Twitter's rate limits

## Additional Resources

- [Twitter API Documentation](https://developer.twitter.com/en/docs)
- [Twitter OAuth 1.0a Guide](https://developer.twitter.com/en/docs/authentication/oauth-1-0a)
- [Twitter Permissions Guide](https://developer.twitter.com/en/docs/authentication/permissions)
