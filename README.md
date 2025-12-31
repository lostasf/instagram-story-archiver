# Gendis Instagram Story Archiver

Archive Instagram stories from one or more accounts (default: `jkt48.gendis`) and automatically post them to Twitter/X in organized threads.

## ✨ Features

- 📸 **Automatic Story Archiving**: GitHub Actions fetches new stories every 8 hours
- 🐦 **Next-Day Twitter Threads**: Posts stories to Twitter at the start of the next day
- 💾 **Archive Database**: Keeps track of all archived stories and local media
- ⚙️ **Scheduled Logic**: Hits Instagram API every 8 hours, posts at 00:00 AM (start of next day)
- 🖼️ **Media Optimization**: Automatically compresses images to meet Twitter size limits
- 📝 **Customizable Captions**: Per-user caption templates (Gendis, Lana, etc.)
- 📊 **Status Tracking**: Maintains statistics and logs of all operations
- 🔄 **Auto-commit**: Archive updates tracked in git history
- 🎬 **Multi-Media Support**: Handles Instagram stories with 4+ media items (batches images, threads videos)

## 🚀 Quick Start (GitHub Actions)

### 1. Fork Repository

Click the "Fork" button on GitHub to create your own copy.

### 2. Add Secrets

Go to **Settings → Secrets and variables → Actions** and add:

**Secrets:**
- `RAPIDAPI_KEY` - Your RapidAPI Instagram key
- `TWITTER_API_KEY` - Twitter Consumer Key
- `TWITTER_API_SECRET` - Twitter Consumer Secret
- `TWITTER_ACCESS_TOKEN` - Twitter Access Token
- `TWITTER_ACCESS_SECRET` - Twitter Access Token Secret
- `TWITTER_BEARER_TOKEN` - Twitter Bearer Token

**Variables:**
- `INSTAGRAM_USERNAME` - `jkt48.gendis` (single username; also accepts comma-separated list for backward compatibility)
- `INSTAGRAM_USERNAMES` - `jkt48.gendis,jkt48.lana.a` (comma-separated list for multi-account)
- `TWITTER_THREAD_CONFIG` - optional JSON to customize per-account anchor tweet text

### 3. Done! 🎉

The workflow runs automatically every hour. Check the **Actions** tab to see runs.

For detailed setup, see [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)

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
# Run once (as GitHub Actions does)
python main.py

# Archive specific story (defaults to primary configured account)
python main.py --story-id <story_id>

# Archive specific story for a specific Instagram user
python main.py --username <instagram_username> --story-id <story_id>

# View archive statistics
python main.py --status

# Test setup
python test_setup.py
```

## How It Works

### Story Fetching and Posting Flow

1. **Check Instagram (Every 8 hours)**: API queries all configured Instagram accounts for new stories.
2. **Download Media**: Images/videos from stories are downloaded and saved to a local cache.
3. **Optimize**: Images are compressed to meet Twitter's 5MB limit.
4. **Archive**: Story metadata and local file paths are stored in `archive.json`.
5. **Post to Twitter (Start of Next Day)**: 
   - When the script runs, it checks for archived stories that haven't been posted yet.
   - If a story's timestamp is from a **previous day**, it is posted to its account's Twitter thread.
   - Each story gets a customized caption based on the Instagram user.
6. **Cleanup**: After successful posting, local media files are removed.

### Thread Structure

Each Instagram account gets its own thread:
- **Anchor tweet**: One tweet per Instagram account (customizable)
- **Story tweets**: Each story is posted as a reply in that account's thread, with the story timestamp and media

### Rate Limiting

- **Instagram API**: 1000 requests/month (shared quota)
- **Twitter API**: Subject to Twitter rate limits (media uploads typically allow 1500/15min)
- **Check Interval**: Optimized to 8 hours (3 times per day) to conserve Instagram API quota

## Project Structure

```
.
├── main.py                  # Entry point and scheduler
├── config.py               # Configuration management
├── story_archiver.py       # Main archiver logic
├── instagram_api.py        # Instagram API wrapper
├── twitter_api.py          # Twitter API wrapper
├── media_manager.py        # Media download and compression
├── archive_manager.py      # Archive database management
├── test_setup.py           # Configuration and API verification
├── diagnose_twitter_oauth.py # Twitter OAuth diagnostic tool
├── requirements.txt        # Python dependencies
├── .env.example            # Example configuration
├── TWITTER_OAUTH_FIX.md    # Twitter OAuth permissions fix guide
├── archive.json            # Archive database (auto-created)
├── archiver.log            # Application logs
├── test_media.jpg          # Test media for OAuth verification
└── media_cache/            # Temporary media storage (auto-created)
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

## Logging

Logs are written to both console and `archiver.log`:

```
2024-01-15 10:30:00 - story_archiver - INFO - Processing story 2921414441985452983 from jkt48.gendis
2024-01-15 10:30:05 - media_manager - INFO - Downloaded image to ./media_cache/2921414441985452983_0.jpg (1.2 MB)
2024-01-15 10:30:10 - twitter_api - INFO - Tweet posted successfully. ID: 1234567890
```

## Multi-Media Story Handling

The archiver correctly handles Instagram stories with multiple media items (4+ images or videos):

### How It Works

**Archive Stage:**
- Downloads **ALL** media items from a story (not just the first)
- Stores multiple local paths and media types
- Maintains backward compatibility with older archive format

**Post Stage:**
- **Images**: Batches up to 4 images per tweet (Twitter limit)
  - 1-4 images → 1 tweet
  - 5-8 images → 2 tweets
  - 9+ images → multiple tweets
- **Videos**: Posts 1 video per tweet (Twitter limitation)
- Creates threaded tweets with progress indicators: `(1/2)`, `(2/2)`

### Example

If an Instagram story has 5 images:
1. Archive downloads all 5 images
2. Posts to Twitter as 2 tweets in a thread:
   - Tweet 1: 4 images + caption + `(1/2)`
   - Tweet 2: 1 image + caption + `(2/2)`
   
Both tweets are replies in the same thread.

See [MULTI_MEDIA_HANDLING.md](MULTI_MEDIA_HANDLING.md) for detailed documentation.

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
5. Run `python diagnose_twitter_oauth.py` to verify

**Detailed instructions**: See [TWITTER_OAUTH_FIX.md](TWITTER_OAUTH_FIX.md)

### "Rate limit exceeded"

- Increase `CHECK_INTERVAL_HOURS` to reduce API calls
- Verify your RapidAPI subscription is active
- Check remaining quota at https://rapidapi.com/dashboard

### "Failed to upload media"

- Ensure images are under 5MB (auto-compressed)
- Check Twitter API permissions include media upload
- Verify `TWITTER_BEARER_TOKEN` is correct
- Use `python diagnose_twitter_oauth.py` to test permissions

### "Story already archived"

- Normal behavior - the archiver tracks processed stories
- Check `archive.json` for details
- Stories will only be processed once

### Connection timeouts

- Check internet connection
- Verify API endpoints are accessible
- Increase timeout values in code if needed

### Diagnostic Tools

```bash
# Test all configurations and API connections
python test_setup.py

# Diagnose Twitter OAuth permissions specifically
python diagnose_twitter_oauth.py
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
- [ ] Story filtering (time-based, caption-based)
- [ ] Web dashboard for status monitoring
- [ ] Database backup and restoration
- [ ] Webhook notifications on errors
- [ ] Instagram Stories reels/video support optimization

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
