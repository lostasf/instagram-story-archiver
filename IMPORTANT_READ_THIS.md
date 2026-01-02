# 🚨 IMPORTANT: Fix Your Twitter OAuth Permissions

## Your Error
```
Twitter API Permission Error (403 Forbidden)
This error indicates your Twitter app permissions need to be updated.
```

## The Problem
Your Twitter app does not have **write permissions**, which are required to post tweets and upload media.

## Quick Fix (5 Minutes)

### 1️⃣ Change App Permissions
- Go to: https://developer.twitter.com/en/portal/dashboard
- Select your app
- Go to: **Settings** > **App permissions**
- Change: "Read" → **"Read and Write"**
- Click: **Save**

### 2️⃣ Configure OAuth 1.0a
- Go to: **Settings** > **User authentication settings**
- Enable: **OAuth 1.0a**
- Set: **App permissions** → "Read and Write"
- Set: **Type of App** → "Web App, Automated App or Bot"
- Set: **Callback URI** → `https://example.com/callback`
- Set: **Website URL** → `https://example.com`
- Click: **Save**

### 3️⃣ REGENERATE TOKENS (Critical!)
- Go to: **Settings** > **Keys and tokens**
- Click: **Regenerate** next to **Access Token and Secret** (OAuth 1.0a section)
- Copy: **New Access Token**
- Copy: **New Access Token Secret**
- (Optional) Regenerate **Bearer Token** and copy it

### 4️⃣ Update GitHub Secrets
- Go to your GitHub repository
- **Settings** > **Secrets and variables** > **Actions**
- Update: `TWITTER_ACCESS_TOKEN` (paste new value)
- Update: `TWITTER_ACCESS_SECRET` (paste new value)
- Update: `TWITTER_BEARER_TOKEN` (paste new value)

### 5️⃣ Verify
Run this command to test:
```bash
python main.py --verify-twitter
```

Expected output:
```
✓ Twitter API credentials are valid
✓ Your Twitter app has the correct permissions
```

## ⚠️ Critical Warning

**After changing permissions, you MUST regenerate your Access Token and Secret!**

- Old tokens = old permissions
- Old tokens will NOT work with new permissions
- This is the most common mistake!

## 📚 More Help

- **Quick Checklist**: See `QUICK_FIX_CHECKLIST.md`
- **Detailed Guide**: See `TWITTER_OAUTH_PERMISSIONS_FIX.md`
- **What Changed**: See `OAUTH_FIX_CHANGES.md`

## 🔧 New Features Added

### 1. Verify Credentials Command
```bash
python main.py --verify-twitter
```
Tests your Twitter API credentials and shows detailed error messages if something is wrong.

### 2. Better Error Messages
The error messages now provide step-by-step fix instructions when permissions are incorrect.

### 3. Comprehensive Documentation
Three new guides to help you troubleshoot:
- `QUICK_FIX_CHECKLIST.md` - Quick reference checklist
- `TWITTER_OAUTH_PERMISSIONS_FIX.md` - Detailed guide with explanations
- `OAUTH_FIX_CHANGES.md` - Summary of all changes made

## 🐛 Still Having Issues?

1. Check the error message carefully
2. Make sure you followed ALL steps in order
3. Wait 1-2 minutes for new tokens to become active
4. Run `python main.py --verify-twitter` for detailed diagnostics

## ✅ Success Indicators

When fixed, you should see:
```
INFO - Media uploaded successfully. ID: 1234567890
INFO - Tweet posted successfully. ID: 1234567891
```

And your GitHub Actions should succeed!

---

**Remember**: The key is to change permissions AND regenerate tokens. Old tokens won't work!
