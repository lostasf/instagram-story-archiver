# Twitter OAuth 1.0a Permissions Fix

## Problem

If you're seeing the error:
```
403 Forbidden
Your client app is not configured with the appropriate oauth1 app permissions for this endpoint.
```

This means your Twitter app doesn't have the correct OAuth 1.0a permissions configured.

## Solution

### Step 1: Check Current App Permissions

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Select your app
3. Go to **"App permissions"** section
4. Ensure it's set to **"Read and Write"** (not just "Read")

### Step 2: Update App Permissions

If permissions are not set to "Read and Write":

1. Click **"Edit"** on the App permissions section
2. Select **"Read and Write"**
3. Click **"Save"**

### Step 3: Regenerate Access Tokens

**IMPORTANT**: After changing permissions, you MUST regenerate your access tokens:

1. Go to **"Keys and tokens"** section
2. Under **"Authentication Tokens"**, click **"Regenerate"** for:
   - Access Token and Secret
3. Copy the new values to your `.env` file

### Step 4: Update Environment Variables

Update your `.env` file with the new tokens:

```bash
TWITTER_ACCESS_TOKEN=your_new_access_token
TWITTER_ACCESS_SECRET=your_new_access_secret
```

### Step 5: Test Configuration

Run the verification command to test your credentials:

```bash
python main.py --verify-twitter
```

Or run the full test script:

```bash
source venv/bin/activate
python test_setup.py
```

## Why This Happens

The application uses both:
- **OAuth 2.0** (Bearer token) for posting tweets via Twitter API v2
- **OAuth 1.0a** (Access tokens) for uploading media via Twitter API v1.1

Media uploads still require OAuth 1.0a permissions, so your app must have "Read and Write" permissions, not just "Read".

## Alternative Solutions

If you continue to have issues, consider:

1. **Create a new Twitter app** with correct permissions from the start
2. **Use Twitter API v2 media upload** (more complex but fully OAuth 2.0)
3. **Check app callback URLs** are properly configured if using 3-legged OAuth

## Common Mistakes

- ❌ Forgetting to regenerate tokens after changing permissions
- ❌ Using "Read" permissions instead of "Read and Write"
- ❌ Not updating the `.env` file with new tokens
- ❌ Using Bearer token instead of Access tokens for media upload

## Verification

After fixing, the application should work without the 403 error. You'll see logs like:

```
INFO - Media uploaded successfully. ID: 1234567890
INFO - Tweet posted successfully. ID: 1234567891
```

Instead of:

```
ERROR - OAuth 1.0a permission error: 403 Forbidden
```