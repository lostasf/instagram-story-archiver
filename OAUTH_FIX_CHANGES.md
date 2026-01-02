# OAuth Permission Fix - Summary of Changes

## Problem
The user encountered a `403 Forbidden` error when trying to post to Twitter, indicating that the Twitter app does not have write permissions.

## Root Cause
The Twitter app permissions are likely set to "Read" instead of "Read and Write", OR the Access Token and Secret weren't regenerated after changing permissions.

## Changes Made

### 1. Enhanced Twitter API (`twitter_api.py`)

#### Added `verify_credentials()` method
- Verifies Twitter API credentials and permissions
- Tests both OAuth 2.0 (v2 API) and OAuth 1.0a (v1.1 API)
- Provides detailed error messages with step-by-step fix instructions
- Handles `tweepy.Forbidden` (403) and `tweepy.Unauthorized` (401) errors specifically

#### Improved error handling in `post_tweet()` method
- Added specific handling for `tweepy.Forbidden` (403) errors
- Provides detailed fix instructions when permissions are incorrect
- Separates authentication errors from other errors

#### Improved error handling in `upload_media()` method
- Added specific handling for `tweepy.Forbidden` (403) errors during media upload
- Provides detailed fix instructions when OAuth 1.0a permissions are incorrect
- Maintains backward compatibility with legacy error messages

### 2. Added Twitter verification CLI flag (`main.py`)

#### New `--verify-twitter` flag
- Allows users to verify Twitter API credentials without running the full archiver
- Exits with code 0 on success, 1 on failure
- Provides clear success/failure messages
- Useful for debugging and troubleshooting

### 3. Created comprehensive troubleshooting guide (`TWITTER_OAUTH_PERMISSIONS_FIX.md`)

Complete guide covering:
- Root cause explanation
- Step-by-step fix instructions with screenshots descriptions
- Common mistakes and how to avoid them
- Twitter API architecture explanation
- Troubleshooting commands
- Additional resources

### 4. Updated documentation (`README.md`)

- Updated troubleshooting section to reference the new guide
- Changed diagnostic commands to use `--verify-twitter` flag
- Added warning about regenerating tokens after changing permissions
- Linked to detailed guide

## How to Use

### Verify Twitter credentials
```bash
python main.py --verify-twitter
```

### Expected output on success
```
✓ Twitter API credentials are valid
✓ Your Twitter app has the correct permissions
```

### Expected output on failure
Detailed error message with step-by-step fix instructions.

## User Action Required

The user needs to:

1. **Go to Twitter Developer Portal**: https://developer.twitter.com/en/portal/dashboard
2. **Change app permissions**: Settings > App permissions > "Read and Write"
3. **Configure OAuth 1.0a**: Settings > User authentication settings > Enable OAuth 1.0a with "Read and Write"
4. **REGENERATE TOKENS**: Settings > Keys and tokens > Click "Regenerate" for Access Token and Secret
5. **Update GitHub Actions secrets**: Update `TWITTER_ACCESS_TOKEN` and `TWITTER_ACCESS_SECRET`
6. **Verify**: Run `python main.py --verify-twitter` to confirm the fix

## Critical Notes

⚠️ **After changing permissions, you MUST regenerate the Access Token and Secret!**
- Old tokens are tied to old permissions
- They will NOT work with new permissions
- This is the most common mistake users make

## Testing

The code has been verified to:
- Compile without syntax errors
- Follow existing code style and conventions
- Maintain backward compatibility
- Provide helpful error messages
- Work with the existing CLI interface

## Files Changed

1. `twitter_api.py` - Enhanced with verification and better error handling
2. `main.py` - Added `--verify-twitter` flag
3. `TWITTER_OAUTH_PERMISSIONS_FIX.md` - New comprehensive troubleshooting guide
4. `README.md` - Updated documentation and references

## Files Unchanged (but relevant)

- `config.py` - No changes needed
- `.env.example` - Already contains correct environment variables
- `diagnose_twitter_oauth.py` - Still available as alternative diagnostic tool
