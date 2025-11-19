# Gendis Instagram Story Archiver

Archive Instagram stories from `jkt48.gendis` and automatically post them to Twitter/X in organized threads.

## Features

- 📸 **Automatic Story Archiving**: Fetches new stories from Instagram every hour
- 🐦 **Twitter Thread Creation**: Posts each story as a thread with media
- 💾 **Archive Database**: Keeps track of all archived stories
- ⚙️ **Scheduled Execution**: Runs automatically on a configurable interval
- 🖼️ **Media Optimization**: Automatically compresses images to meet Twitter size limits
- 📊 **Status Tracking**: Maintains statistics and logs of all operations

## Requirements

- Python 3.8+
- Instagram API access via RapidAPI (1000 requests/month)
- Twitter API v2 access with media upload permissions

## Setup

### 1. Clone and Install Dependencies

```bash
git clone <repository>
cd gendis-instagram-story-archiver
pip install -r requirements.txt
```

### 2. Configure API Credentials

Copy the example configuration and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# RapidAPI Instagram Configuration
RAPIDAPI_KEY=your_api_key_here
RAPIDAPI_HOST=instagram120.p.rapidapi.com

# Twitter/X API Configuration
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
TWITTER_BEARER_TOKEN=your_bearer_token

# Configuration
INSTAGRAM_USERNAME=jkt48.gendis
CHECK_INTERVAL_HOURS=1
ARCHIVE_DB_PATH=./archive.json
MEDIA_CACHE_DIR=./media_cache
```

### 3. Get API Credentials

#### Instagram API (RapidAPI)

1. Go to [RapidAPI](https://rapidapi.com)
2. Search for "Instagram" and select an Instagram API
3. Subscribe to the free tier (1000 requests/month)
4. Copy your API key and host from the API dashboard

#### Twitter API v2

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new app or use an existing one
3. Generate API keys and access tokens with media upload permissions
4. Enable OAuth 1.0a user context authentication

## Usage

### Run Once

```bash
python main.py --once
```

### Archive Specific Story

```bash
python main.py --story-id <story_id>
```

### View Archive Status

```bash
python main.py --status
```

### Start Scheduled Archiver (Default)

```bash
python main.py
```

This will run indefinitely, checking for new stories every hour.

## How It Works

### Story Fetching Flow

1. **Check Instagram**: API queries `jkt48.gendis` for new stories
2. **Download Media**: All images/videos from stories are downloaded
3. **Optimize**: Images are compressed to meet Twitter's 5MB limit
4. **Create Thread**: Stories are posted as Twitter threads
5. **Archive**: Story IDs and tweet references are stored in `archive.json`

### Thread Structure

Each archived story becomes a Twitter thread:
- **Post 1**: Introduction with story info and item count
- **Posts 2-N**: Individual media items (images/videos)
- **Final Post**: Completion confirmation

### Rate Limiting

- **Instagram API**: 1000 requests/month (shared quota)
- **Twitter API**: Subject to Twitter rate limits (media uploads typically allow 1500/15min)
- **Check Interval**: Configurable (default: 1 hour to conserve quota)

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
├── requirements.txt        # Python dependencies
├── .env.example            # Example configuration
├── archive.json            # Archive database (auto-created)
├── archiver.log            # Application logs
└── media_cache/            # Temporary media storage (auto-created)
```

## Archive Database Format

`archive.json` stores all archived stories:

```json
{
  "archived_stories": [
    {
      "story_id": "2921414441985452983",
      "archived_at": "2024-01-15T10:30:00.123456",
      "media_count": 3,
      "tweet_ids": ["1234567890", "1234567891", "1234567892"],
      "media_urls": ["https://...", "https://..."]
    }
  ],
  "last_check": "2024-01-15T10:30:00.123456"
}
```

## Logging

Logs are written to both console and `archiver.log`:

```
2024-01-15 10:30:00 - story_archiver - INFO - Processing story 2921414441985452983 from jkt48.gendis
2024-01-15 10:30:05 - media_manager - INFO - Downloaded image to ./media_cache/2921414441985452983_0.jpg (1.2 MB)
2024-01-15 10:30:10 - twitter_api - INFO - Tweet posted successfully. ID: 1234567890
```

## Error Handling

The archiver is resilient to errors:

- **API Failures**: Logs error and retries on next scheduled check
- **Download Failures**: Skips problematic media and continues with others
- **Tweet Posting Failures**: Logs error but continues processing
- **Configuration Issues**: Exits immediately with clear error message

## Troubleshooting

### "Rate limit exceeded"

- Increase `CHECK_INTERVAL_HOURS` to reduce API calls
- Verify your RapidAPI subscription is active
- Check remaining quota at https://rapidapi.com/dashboard

### "Failed to upload media"

- Ensure images are under 5MB (auto-compressed)
- Check Twitter API permissions include media upload
- Verify `TWITTER_BEARER_TOKEN` is correct

### "Story already archived"

- Normal behavior - the archiver tracks processed stories
- Check `archive.json` for details
- Stories will only be processed once

### Connection timeouts

- Check internet connection
- Verify API endpoints are accessible
- Increase timeout values in code if needed

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

- [ ] Support for multiple Instagram accounts
- [ ] Custom hashtag/caption templates
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
