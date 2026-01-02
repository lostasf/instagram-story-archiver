# 🔧 Quick Fix Checklist: Twitter OAuth Permissions

## Your Error
```
Twitter API Permission Error (403 Forbidden)
```

## ✅ Follow These Steps (In Order)

### Step 1: Change App Permissions
- [ ] Go to: https://developer.twitter.com/en/portal/dashboard
- [ ] Select your app
- [ ] Go to: **Settings** > **App permissions**
- [ ] Change: "Read" → **"Read and Write"**
- [ ] Click: **Save**

### Step 2: Configure OAuth 1.0a
- [ ] Go to: **Settings** > **User authentication settings**
- [ ] Ensure: OAuth 1.0a is **enabled**
- [ ] Set: **App permissions** → "Read and Write"
- [ ] Set: **Type of App** → "Web App, Automated App or Bot"
- [ ] Set: **Callback URI** → `https://example.com/callback`
- [ ] Set: **Website URL** → `https://example.com`
- [ ] Click: **Save**

### Step 3: REGENERATE TOKENS (Critical!)
- [ ] Go to: **Settings** > **Keys and tokens**
- [ ] Find: **OAuth 1.0a** section
- [ ] Click: **Regenerate** next to **Access Token and Secret**
- [ ] Copy: **New Access Token**
- [ ] Copy: **New Access Token Secret**
- [ ] (Optional) Click: **Regenerate** next to **Bearer Token**
- [ ] Copy: **New Bearer Token**

### Step 4: Update GitHub Secrets
- [ ] Go to your GitHub repository
- [ ] Navigate to: **Settings** > **Secrets and variables** > **Actions**
- [ ] Update: `TWITTER_ACCESS_TOKEN` (paste new value)
- [ ] Update: `TWITTER_ACCESS_SECRET` (paste new value)
- [ ] Update: `TWITTER_BEARER_TOKEN` (paste new value)
- [ ] Click: **Update** for each secret

### Step 5: Verify the Fix
- [ ] Run locally: `python main.py --verify-twitter`
- [ ] Expected output:
  ```
  ✓ Twitter API credentials are valid
  ✓ Your Twitter app has the correct permissions
  ```
- [ ] If successful, your GitHub Actions should now work!

## ⚠️ Critical Reminders

1. **Old tokens won't work with new permissions** - You MUST regenerate them!
2. **Don't skip Step 3** - This is the most common mistake!
3. **Update both local .env AND GitHub secrets** - Make sure both are in sync
4. **Wait a few minutes** - Sometimes it takes 1-2 minutes for new tokens to become active

## 🐛 Still Having Issues?

Run this command for detailed diagnostics:
```bash
python main.py --verify-twitter
```

If it still fails, check the error message carefully:
- **403 Forbidden** → Permissions still incorrect, or tokens not regenerated
- **401 Unauthorized** → Invalid/expired tokens
- **Other errors** → Check logs in `archiver.log`

## 📚 More Information

- **Detailed Guide**: See `TWITTER_OAUTH_PERMISSIONS_FIX.md`
- **Code Changes**: See `OAUTH_FIX_CHANGES.md`
- **Full Documentation**: See `README.md`

## 🔗 Useful Links

- [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
- [Twitter OAuth 1.0a Guide](https://developer.twitter.com/en/docs/authentication/oauth-1-0a)
- [Twitter API Permissions](https://developer.twitter.com/en/docs/authentication/permissions)

---

**Remember**: The key is to change permissions AND regenerate tokens. Old tokens = old permissions!
