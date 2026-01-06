# Twitter OAuth Fix Guide

## Problem: 403 Forbidden Error

If you're seeing this error:
```
403 Forbidden
Your client app is not configured with the appropriate oauth1 app permissions for this endpoint.
```

This means your Twitter app doesn't have the correct OAuth permissions configured. The application uses both OAuth 1.0a (for media upload) and OAuth 2.0 (for posting), both requiring "Read and Write" permissions.

## Quick Fix (5 Minutes)

### Step 1: Change App Permissions
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Select your app
3. Go to **Settings** > **App permissions**
4. Change from "Read" to **"Read and Write"**
5. Click **Save**

### Step 2: Configure OAuth 1.0a Settings
1. Go to **Settings** > **User authentication settings**
2. Enable **OAuth 1.0a**
3. Set **App permissions** to "Read and Write"
4. Set **Type of App** to "Web App, Automated App or Bot"
5. Set **Callback URI** to any valid URL (e.g., `https://example.com/callback`)
6. Set **Website URL** to any valid URL (e.g., `https://example.com`)
7. Click **Save**

### Step 3: REGENERATE TOKENS (CRITICAL!)
⚠️ **This is the most important step!** ⚠️

After changing permissions, you MUST regenerate your access tokens:

1. Go to **Settings** > **Keys and tokens**
2. Under **Authentication Tokens**, click **"Regenerate"** for:
   - Access Token and Secret
   - Bearer Token (optional but recommended)
3. Copy the new values

**Important**: The old tokens will NOT work with the new permissions!

### Step 4: Update Environment Variables
Update your `.env` file with the new tokens:
```bash
TWITTER_ACCESS_TOKEN=your_new_access_token
TWITTER_ACCESS_SECRET=your_new_access_secret
TWITTER_BEARER_TOKEN=your_new_bearer_token
```

### Step 5: Update GitHub Actions Secrets
Update these secrets in your GitHub repository:
```
TWITTER_ACCESS_TOKEN=<new_access_token>
TWITTER_ACCESS_SECRET=<new_access_secret>
TWITTER_BEARER_TOKEN=<new_bearer_token>
```

Keep these unchanged:
- `TWITTER_API_KEY` (Consumer Key)
- `TWITTER_API_SECRET` (Consumer Secret)

### Step 6: Test Configuration
Run the verification command:
```bash
python main.py --verify-twitter
```

## How It Works

This project uses two different Twitter API approaches:

1. **OAuth 1.0a (v1.1 API)** - Used for media upload
   - Requires: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`
   - Used by: `twitter_api.v1_client.media_upload()`

2. **OAuth 2.0 (v2 API)** - Used for posting tweets
   - Requires: `TWITTER_BEARER_TOKEN` and/or OAuth 1.0a credentials
   - Used by: `twitter_api.client.create_tweet()`

Both need "Read and Write" permissions to work correctly.

## Verification

### Success Output
```
Verifying Twitter API credentials...
✓ Twitter API credentials are valid
✓ Your Twitter app has the correct permissions
```

### Error Output (if permissions are wrong)
```
Twitter API Permission Error (403 Forbidden)
THIS ERROR MEANS YOUR TWITTER APP DOES NOT HAVE WRITE PERMISSIONS

TO FIX THIS ISSUE:
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Select your app
3. Go to 'Settings' > 'App permissions'
4. Change permissions from 'Read' to 'Read and Write'
...
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

## Alternative Solutions

If you continue to have issues, consider:

1. **Create a new Twitter app** with correct permissions from the start
2. **Use Twitter API v2 media upload** (more complex but fully OAuth 2.0)
3. **Check app callback URLs** are properly configured if using 3-legged OAuth

## Troubleshooting Commands

### Check current configuration
```bash
python main.py --status
```

### Verify Twitter credentials
```bash
python main.py --verify-twitter
```

### Test locally
```bash
# Archive only (won't post to Twitter)
python main.py --fetch-only

# Test full setup
python test_setup.py
```

## Diagnostic Tools

The project includes several tools for troubleshooting Twitter OAuth issues:

### `--verify-twitter` flag
Quick credential verification without running the full archiver:
```bash
python main.py --verify-twitter
```

### `diagnose_twitter_oauth.py`
Detailed OAuth diagnostic tool:
```bash
python diagnose_twitter_oauth.py
```

### `test_setup.py`
Complete configuration and API verification:
```bash
python test_setup.py
```

## Still Having Issues?

1. **Check the logs**: Look at `archiver.log` for detailed error messages
2. **Verify all secrets**: Make sure all 5 Twitter secrets are set correctly
3. **Try a manual test**: Use Twitter's API explorer to test your credentials
4. **Check rate limits**: You might be hitting Twitter's rate limits
5. **Wait a few minutes**: Sometimes it takes 1-2 minutes for new tokens to become active

## Additional Resources

- [Twitter API Documentation](https://developer.twitter.com/en/docs)
- [Twitter OAuth 1.0a Guide](https://developer.twitter.com/en/docs/authentication/oauth-1-0a)
- [Twitter Permissions Guide](https://developer.twitter.com/en/docs/authentication/permissions)

## What Was Enhanced

This guide was created by merging multiple documentation files to provide a comprehensive solution. The enhanced features include:

- **Better error handling** in the code with specific 403 error detection
- **Verification tools** (`--verify-twitter` flag) for quick testing
- **Detailed diagnostic scripts** for troubleshooting
- **Comprehensive documentation** covering all common scenarios

The key improvement is the `--verify-twitter` flag that allows you to test your Twitter API credentials without running the full archiving process, making troubleshooting much faster.