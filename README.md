# Gendis Instagram Story Archiver

Archive Instagram stories from one or more accounts (default: `jkt48.gendis`) and automatically post them to Twitter/X in organized threads.

## ✨ Features

- 📸 **Automatic Story Archiving**: GitHub Actions fetches new stories every 8 hours
- 🐦 **Daily Twitter Posting**: Posts stories from previous days at 00:00 UTC+7 grouped by day
- 💾 **Archive Database**: Keeps track of all archived stories and local media
- ⚙️ **Three-Workflow System**: Separate workflows for archiving (`--fetch-only`), posting (`--post-daily`), and weekly cleanup (`--archive-only --cleanup-only`)
- 🖼️ **Media Optimization**: Automatically compresses images to meet Twitter size limits
- 📝 **Customizable Captions**: Per-user caption templates (Gendis, Lana, etc.)
- 📊 **Status Tracking**: Maintains statistics and logs of all operations
- 🔄 **Auto-commit**: Archive updates tracked in git history
- 🎬 **Multi-Media Support**: Handles Instagram stories with mixed images and videos (batches up to 4 items per tweet)
- 📅 **Next-Day Posting**: Stories uploaded today are logged as "planned for next day" and posted at 00:00 UTC+7
- 🧹 **Weekly Cleanup**: Automatic media cache cleanup and repository maintenance

## 🚀 Quick Start (GitHub Actions)

### 1. Fork Repository

Click the "Fork" button on GitHub to create your own copy.

### 2. Add Secrets

Go to **Settings → Secrets and variables → Actions** and add:

**Secrets:**
- `RAPIDAPI_KEY` - Your RapidAPI Instagram key
- `RAPIDAPI_HOST` - `instagram120.p.rapidapi.com` (or your API host)
- `TWITTER_API_KEY` - Twitter Consumer Key
- `TWITTER_API_SECRET` - Twitter Consumer Secret
- `TWITTER_ACCESS_TOKEN` - Twitter Access Token
- `TWITTER_ACCESS_SECRET` - Twitter Access Token Secret
- `TWITTER_BEARER_TOKEN` - Twitter Bearer Token
- `HTTP_PROXY` - (Optional) HTTP proxy URL to prevent Cloudflare blocking (e.g., `http://proxy.example.com:8080`)
- `HTTPS_PROXY` - (Optional) HTTPS proxy URL to prevent Cloudflare blocking (e.g., `http://proxy.example.com:8080`)

**Variables:**
- `INSTAGRAM_USERNAME` - `jkt48.gendis` (single username; also accepts comma-separated list for backward compatibility)
- `INSTAGRAM_USERNAMES` - `jkt48.gendis,jkt48.lana.a` (comma-separated list for multi-account)
- `TWITTER_THREAD_CONFIG` - optional JSON to customize per-account anchor tweet text

### 3. Done! 🎉

The workflows run automatically:
- **Archive workflow**: Every 8 hours (fetches stories only)
- **Post workflow**: Daily at 00:00 UTC+7 (posts stories from previous days)
- **Robust Progress Persistence**: If the posting process fails partway (e.g., due to rate limits), the script automatically commits and pushes successful progress to the repository before exiting with an error. This ensures that the next run picks up from where it left off, avoiding duplicate posts and respecting API quotas.

Check the **Actions** tab to see runs.

For detailed setup, see [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) or [QUICKSTART.md](QUICKSTART.md)

## 💻 Local Development

### Setup

```bash
git clone <repository>
cd gendis-instagram-story-archiver
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

### Usage

```bash
# Archive only (fetch stories, don't post)
python main.py --fetch-only

# Post stories from previous days (grouped by day)
python main.py --post-daily

# Archive and post in one run
python main.py

# Archive specific story
python main.py --story-id <story_id>

# Archive specific story for a specific Instagram user
python main.py --username <instagram_username> --story-id <story_id>

# View archive statistics
python main.py --status

# Verify Twitter API credentials and permissions
python main.py --verify-twitter

# Test setup
python test_setup.py

# Run media cache cleanup only
python main.py --cleanup-only
```

## Repository State

### Current Status (January 2025)

This repository represents a **production-ready Instagram story archiving system** with comprehensive automation and error handling. The system is actively maintained with three separate GitHub Actions workflows that ensure reliable story collection and posting.

### Key Achievements

✅ **Fully Automated**: Three-workflow system handles archiving, posting, and maintenance
✅ **Multi-Account Support**: Handles multiple Instagram accounts simultaneously
✅ **Robust Error Handling**: Graceful degradation and comprehensive logging
✅ **Twitter OAuth Ready**: Includes diagnostic tools for OAuth troubleshooting
✅ **Media Optimization**: Automatic image compression and multi-media batching
✅ **Repository Maintenance**: Weekly cleanup ensures clean git history

### Technical Maturity

- **Type hints**: Throughout the codebase for better maintainability
- **Comprehensive documentation**: README, quick start, developer notes, and AI agent guide
- **Testing tools**: Setup verification and OAuth diagnostic scripts
- **Security conscious**: Environment variables, no hardcoded secrets
- **Performance optimized**: Batched media uploads and efficient API usage

### Recent Enhancements (2024-2025)

1. **Three-Workflow Architecture**: Separated archiving, posting, and cleanup for better reliability
2. **Enhanced Multi-Media Support**: Batches up to 4 media items per tweet
3. **Twitter OAuth Tools**: Added verification and diagnostic capabilities
4. **Improved Timezone Logic**: "Previous days" instead of just "yesterday"
5. **Repository Health**: Weekly cleanup workflow maintains clean git history

## Documentation

### GitHub Actions Workflows

This project uses **three separate GitHub Actions workflows** for optimal automation:

#### 1. Archive Workflow (`archive-stories.yml`)
- **Schedule**: Every 8 hours (cron: `0 */8 * * *` UTC)
- **Command**: `python main.py --fetch-only`
- **Purpose**: Fetch and archive new stories from Instagram
- **Does NOT post** to Twitter

#### 2. Post Workflow (`post-stories.yml`)
- **Schedule**: Daily at 00:00 UTC+7 (cron: `0 17 * * *` UTC)
- **Command**: `python main.py --post-daily`
- **Purpose**: Post stories from previous days grouped by day
- **Posts** to Twitter with batched media (up to 4 items per tweet)

#### 3. Weekly Cleanup Workflow (`cleanup-media-cache.yml`)
- **Schedule**: Weekly on Sundays at 02:00 UTC (09:00 UTC+7)
- **Command**: `python main.py --archive-only --cleanup-only`
- **Purpose**: Clean up media cache and push changes to repository
- **Commits** file deletions and updates to git history

### Story Processing Flow

**Archiving Stage** (runs every 8 hours):
1. **Check Instagram**: API queries all configured Instagram accounts for new stories
2. **Download Media**: Images/videos from stories are downloaded and saved to `media_cache/`
3. **Optimize**: Images are compressed to meet Twitter's 5MB limit
4. **Archive**: Story metadata and local file paths are stored in `archive.json` with `taken_at` field (from Instagram's API)

**Posting Stage** (runs daily at 00:00 UTC+7):
1. **Check Eligible Stories**: Stories where `taken_at < today` (UTC+7) and `tweet_ids` is empty
2. **Group by Day**: All stories from the same day are grouped together
3. **Batch Media**: Up to 4 media items (images or videos) per tweet to minimize tweets
4. **Post to Thread**: Creates/replies to thread with captions only (no progress indicators)
5. **Update Archive**: Saves `tweet_ids` to `archive.json`
6. **Cleanup**: Deletes media files from `media_cache/` and clears `local_media_paths`

**Key Logic**:
- Stories uploaded **today** (UTC+7) are logged as "planned for next day" - not posted until tomorrow
- Stories uploaded **before today** (UTC+7) are posted in batches when the workflow runs at 00:00 UTC+7
- This ensures a complete day's stories are posted together in organized threads

### Thread Structure

Each Instagram account gets its own thread:
- **Anchor tweet**: One tweet per Instagram account (customizable via `TWITTER_THREAD_CONFIG`)
- **Story tweets**: All stories from the same day are posted as replies in that account's thread
- **Media batching**: Up to 4 media items (images or videos) per tweet without progress indicators
- **One thread per day**: All stories from the same day are grouped into a single thread

### Rate Limiting

- **Instagram API**: 1000 requests/month (shared quota)
- **Twitter API**: Subject to Twitter rate limits (media uploads typically allow 1500/15min)
- **Archive Workflow**: Runs every 8 hours (3 times per day) to conserve Instagram API quota
- **Post Workflow**: Runs once daily at 00:00 UTC+7

## Project Structure

```
.
├── main.py                      # Entry point with CLI flags (--fetch-only, --post-daily, etc.)
├── config.py                    # Configuration management
├── story_archiver.py            # Main archiver logic
├── instagram_api.py             # Instagram API wrapper
├── twitter_api.py               # Twitter API wrapper
├── media_manager.py             # Media download and compression
├── archive_manager.py           # Archive database management
├── test_setup.py                # Configuration and API verification
├── diagnose_twitter_oauth.py    # Twitter OAuth diagnostic tool
├── requirements.txt             # Python dependencies
├── .env.example                 # Example configuration
├── TWITTER_OAUTH_FIX_GUIDE.md    # Twitter OAuth permissions fix guide
├── DEVELOPER_NOTES.md           # Technical notes for developers
├── AI_AGENT_GUIDE.md            # Quick reference for AI agents
├── archive.json                 # Archive database (auto-created)
├── archiver.log                 # Application logs
├── test_media.jpg               # Test media for OAuth verification
├── media_cache/                 # Temporary media storage (auto-created)
└── .github/workflows/
    ├── archive-stories.yml      # Runs every 8 hours: python main.py --fetch-only
    ├── post-stories.yml         # Runs daily at 00:00 UTC+7: python main.py --post-daily
    └── cleanup-media-cache.yml  # Runs weekly: python main.py --archive-only --cleanup-only
```

## Archive Database Format

`archive.json` stores all archived stories, grouped by Instagram account:

```json
{
  "schema_version": 2,
  "accounts": {
    "jkt48.gendis": {
      "anchor_tweet_id": "1234567890",
      "last_tweet_id": "1234567899",
      "last_check": "2024-01-15T10:30:00.123456",
      "archived_stories": [
        {
          "story_id": "2921414441985452983",
          "instagram_username": "jkt48.gendis",
          "archived_at": "2024-01-15T10:30:00.123456",
          "taken_at": 1700000000,
          "media_count": 1,
          "tweet_ids": ["1234567899"],
          "media_urls": ["https://..."]
        }
      ]
    },
    "jkt48.lana.a": {
      "anchor_tweet_id": "2234567890",
      "last_tweet_id": "2234567899",
      "last_check": "2024-01-15T10:30:00.123456",
      "archived_stories": []
    }
  }
}
```

**Important fields for posting logic:**
- `taken_at`: Unix timestamp from Instagram API - used for "next day" posting logic
- `tweet_ids`: Empty array `[]` means story hasn't been posted yet
- Stories are only posted if `taken_at < today` (UTC+7) and `tweet_ids` is empty

## Logging

Logs are written to both console and `archiver.log`:

```
2024-01-15 10:30:00 - story_archiver - INFO - Processing story 2921414441985452983 from jkt48.gendis
2024-01-15 10:30:05 - media_manager - INFO - Downloaded image to ./media_cache/2921414441985452983_0.jpg (1.2 MB)
2024-01-15 10:30:10 - twitter_api - INFO - Tweet posted successfully. ID: 1234567890
```

## Multi-Media Story Handling

The archiver correctly handles Instagram stories with multiple media items (mixed images and videos):

### How It Works

**Archive Stage:**
- Downloads **ALL** media items from a story (not just the first)
- Stores multiple local paths and media types
- Maintains backward compatibility with older archive format

**Post Stage:**
- **Media Batching**: Batches up to 4 media items (images or videos) per tweet.
- **Unified Threads**: Photos and videos can be mixed in the same tweet to minimize the total number of tweets in a thread.
- No part indicators on tweets.

### Example

If an Instagram story has 2 images and 1 video:
1. Archive downloads all 3 media items
2. Posts to Twitter as 1 tweet (since total is <= 4):
   - Tweet 1: 2 images + 1 video + caption

If an Instagram story has 5 items (e.g., 4 images and 1 video):
1. Posts to Twitter as 2 tweets:
   - Tweet 1: 4 images + caption
   - Tweet 2: 1 video + caption

Both tweets are replies in the same thread.

## Customizing Caption Templates

You can customize the text template for each Instagram account by modifying `config.py`.

### How to Update

1. Open `config.py`
2. Locate the `get_story_caption` method
3. Modify the return string for the desired username
4. The template uses f-strings and supports `{date_str}` (DD/MM/YYYY)

Example for Gendis:
```python
if 'gendis' in username.lower():
    return f"Instagram Story @Gendis_JKT48\n{date_str}\n\n#Mantrajiva"
```

Result:
```
Instagram Story @Gendis_JKT48
DD/MM/YYYY

#Mantrajiva
```

## Error Handling

The archiver is resilient to errors:

- **API Failures**: Logs error and retries on next scheduled check
- **Download Failures**: Skips problematic media and continues with others
- **Tweet Posting Failures**: Logs error but continues processing
- **Configuration Issues**: Exits immediately with clear error message

## Troubleshooting

### "403 Forbidden - OAuth1 app permissions" (COMMON)

**Problem**: `Your client app is not configured with the appropriate oauth1 app permissions for this endpoint`

**Quick Fix**:
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Select your app → **App permissions** → Set to **"Read and Write"**
3. Go to **Keys and tokens** → **Regenerate** Access Token and Secret
4. Update your `.env` file with new tokens
5. Run `python main.py --verify-twitter` to verify

**📖 Detailed Guide**: See [TWITTER_OAUTH_FIX_GUIDE.md](TWITTER_OAUTH_FIX_GUIDE.md) for complete step-by-step instructions.

**⚠️ Critical**: After changing permissions, you MUST regenerate your Access Token and Secret. The old tokens won't work with new permissions!

**🔍 Verification**: Use `python main.py --verify-twitter` to test your credentials and permissions before running the main workflows.

### "Rate limit exceeded"

- Increase archive workflow interval (edit `.github/workflows/archive-stories.yml`)
- Verify your RapidAPI subscription is active
- Check remaining quota at https://rapidapi.com/dashboard

### "Failed to upload media"

- Ensure images are under 5MB (auto-compressed)
- Check Twitter API permissions include media upload (Read and Write)
- Verify `TWITTER_BEARER_TOKEN` is correct
- Use `python main.py --verify-twitter` to test permissions

### "Story already archived"

- Normal behavior - the archiver tracks processed stories
- Check `archive.json` for details
- Stories will only be processed once

### "No stories to post"

- Normal if all stories have already been posted
- Check `archive.json` for `tweet_ids` (empty = not posted)
- Check `taken_at` timestamps - stories from today (UTC+7) won't post until tomorrow

### Connection timeouts

- Check internet connection
- Verify API endpoints are accessible
- Increase timeout values in code if needed

### Diagnostic Tools

```bash
# Test all configurations and API connections
python test_setup.py

# Verify Twitter API credentials and permissions
python main.py --verify-twitter
```

## Performance Notes

- **Memory Usage**: ~100-200MB for typical operations
- **API Quota**: ~10-15 API calls per story (check + fetch + media)
- **Processing Time**: ~1-2 minutes per story depending on media size
- **Storage**: ~50-100MB per month for cache (auto-cleaned)

## Security

- ⚠️ **Never commit `.env`** - it contains sensitive credentials
- 🔒 Use environment variables for secrets in production
- 📝 `.env` is included in `.gitignore`
- 🗝️ Rotate API keys periodically

## Future Enhancements

- [x] Support for multiple Instagram accounts
- [x] Custom hashtag/caption templates
- [x] Handle stories with 4+ media items (multi-media batching)
- [x] Separate archive and post workflows
- [x] Weekly cleanup workflow for media cache management
- [x] Twitter OAuth verification tools
- [ ] Story filtering (time-based, caption-based)
- [ ] Web dashboard for status monitoring
- [ ] Database backup and restoration
- [ ] Webhook notifications on errors
- [ ] Instagram Stories reels/video support optimization
- [ ] Docker containerization support
- [ ] Discord notifications integration

## License

This project is provided as-is for educational and archival purposes.

## Support

For issues or questions:
1. Check the logs in `archiver.log`
2. Verify all configuration is correct in `.env`
3. Test API credentials independently
4. Check API rate limits and quotas

## Disclaimer

This tool is intended for personal archival purposes. Ensure you comply with:
- Instagram's Terms of Service
- Twitter/X's Terms of Service
- Local laws and regulations regarding content archival
- Respect for intellectual property rights
