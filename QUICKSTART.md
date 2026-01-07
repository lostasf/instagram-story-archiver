# Quick Start Guide

Get the Instagram Story Archiver running in 3 minutes using GitHub Actions! 🚀

## Option 1: GitHub Actions (Recommended) ⭐

No local setup required - runs automatically!

### 1. Fork Repository (30 seconds)

Click the "Fork" button to create your own copy.

### 2. Add Secrets (1 minute)

Go to **Settings → Secrets and variables → Actions**

Add these **Secrets**:
```
RAPIDAPI_KEY=your_key
RAPIDAPI_HOST=instagram120.p.rapidapi.com
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_secret
TWITTER_BEARER_TOKEN=your_bearer_token
HTTP_PROXY=http://proxy.example.com:8080  # Optional: Prevent Cloudflare blocking
HTTPS_PROXY=http://proxy.example.com:8080  # Optional: Prevent Cloudflare blocking
```

Add this **Variable**:
```
INSTAGRAM_USERNAME=jkt48.gendis
```

**Optional Variables** (for multi-account):
```
INSTAGRAM_USERNAMES=jkt48.gendis,jkt48.lana.a
TWITTER_THREAD_CONFIG={"jkt48.gendis": {"anchor": "Gendis Stories 🌸"}, "jkt48.lana.a": {"anchor": "Lana Stories ✨"}}
```

### 3. Done! ✅

The workflows will run automatically:
- **Archive workflow**: Every 8 hours (fetches stories only)
- **Post workflow**: Daily at 00:00 UTC+7 (posts stories from previous days)

Go to **Actions** tab to see runs.

**Learn more:** [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)

---

## Option 2: Local Development

### 1. Install Dependencies

```bash
git clone <repository>
cd gendis-instagram-story-archiver
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

### 3. Test Setup

```bash
python test_setup.py
```

Should show:
```
✓ Configuration loaded successfully
✓ Successfully connected to Instagram API
✓ Successfully authenticated to Twitter API
✓ All tests passed! Ready to start archiving.
```

### 4. Run Commands

```bash
# Archive only (fetch stories, don't post)
python main.py --fetch-only

# Post stories from previous days (grouped by day)
python main.py --post-daily

# Archive and post in one run (not recommended for production)
python main.py

# View archive statistics
python main.py --status
```

## Common Commands

### Archive Stories
```bash
# Fetch and archive new stories (no posting)
python main.py --fetch-only

# Archive only mode (same as --fetch-only)
python main.py --archive-only
```

### Post Stories
```bash
# Post stories from previous days grouped by day
python main.py --post-daily

# Post all pending stories (not grouped)
python main.py
```

### View Status
```bash
# View archive statistics
python main.py --status

# View logs in real-time
tail -f archiver.log
```

### Archive Specific Story
```bash
# Archive specific story (defaults to primary account)
python main.py --story-id 2921414441985452983

# Archive specific story for a specific user
python main.py --username jkt48.gendis --story-id 2921414441985452983
```

## Docker (Alternative)

If you prefer Docker:

```bash
# Build and run
docker-compose up

# Or run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## First Run Expected Behavior

### Archive Mode (--fetch-only)
1. ✓ Connects to Instagram API
2. ✓ Fetches stories from configured accounts
3. ✓ Downloads and archives media files to `media_cache/`
4. ✓ Compresses images if needed
5. ✓ Records in `archive.json` with `taken_at` timestamp
6. ✓ Stories logged as "planned for next day" if uploaded today (UTC+7)

Takes 1-3 minutes per story depending on media size.

### Post Mode (--post-daily)
1. ✓ Checks `archive.json` for unposted stories
2. ✓ Finds stories where `taken_at < today` (UTC+7) and `tweet_ids` is empty
3. ✓ Groups stories by day
4. ✓ Batches up to 4 media items per tweet
5. ✓ Posts to Twitter with progress indicators
6. ✓ Updates `archive.json` with `tweet_ids`
7. ✓ Deletes media files from `media_cache/`

Takes 2-5 minutes per day's stories.

## Monitoring

Check these files to monitor progress:

```bash
# Application logs (live updates)
tail -f archiver.log

# Archive database (story tracking)
cat archive.json | python -m json.tool

# Media cache status
ls -lh media_cache/
```

## Troubleshooting

### "ModuleNotFoundError: No module named..."
```bash
pip install -r requirements.txt
```

### "Configuration error: Missing configuration..."
```bash
# Check .env file has all required keys
cat .env | grep -E "RAPIDAPI_KEY|TWITTER_"
```

### "Rate limit exceeded"
```bash
# Increase check interval in GitHub Actions schedule
# Edit .github/workflows/archive-stories.yml
# Change cron from '0 */8 * * *' to '0 */12 * * *' (every 12 hours)
```

### "Authentication failed"
```bash
# Verify credentials in .env are correct
python test_setup.py
```

### "Cloudflare blocking / 403 errors"
```bash
# Add HTTP_PROXY and HTTPS_PROXY secrets to GitHub Actions
# Go to Settings → Secrets and variables → Actions
# Add HTTP_PROXY and HTTPS_PROXY with your proxy server URLs
```

### "No stories to post"
- Normal if all stories have already been posted
- Check `archive.json` for `tweet_ids` field (empty = not posted)
- Check `taken_at` timestamps - stories from today (UTC+7) won't post until tomorrow

## What Gets Archived?

Each day's stories become a Twitter thread:

- **Archive workflow**: Downloads all new stories every 8 hours
- **Post workflow**: Posts stories from previous days in organized threads
  - Up to 4 media items per tweet
  - Progress indicators: `(1/2)`, `(2/2)` for multi-tweet days
  - Custom captions per account

All tracked in `archive.json` with:
- Story ID
- Timestamp (`taken_at`)
- Media count
- Tweet IDs (after posting)
- Original URLs

## Rate Limits

⚠️ Be aware of these limits:

| Service | Limit | Duration |
|---------|-------|----------|
| Instagram API | 1000 | Per month |
| Twitter Media Upload | 1500 | Per 15 minutes |
| Archive Workflow | Every 8 hours | Configurable |
| Post Workflow | Daily at 00:00 UTC+7 | Configurable |

**Estimated Usage**:
- ~3 requests/day at 8-hour intervals (archive workflow)
- ~90 requests/month (well under 1000 limit)
- Plenty of room for multiple accounts

## Advanced Usage

### Run with custom settings

```bash
# 1. Edit .env
INSTAGRAM_USERNAME=different_user

# 2. Run
python main.py --fetch-only
```

### Run in background (Linux/Mac)

```bash
# Start in background
nohup python main.py --fetch-only > archiver.log 2>&1 &

# Stop later
pkill -f "python main.py"
```

### Schedule with cron (Linux/Mac)

```bash
# Run archive-only every 6 hours
0 */6 * * * cd /path/to/project && python main.py --fetch-only

# Run post-daily at 00:00 UTC+7 (17:00 UTC)
0 17 * * * cd /path/to/project && python main.py --post-daily

# Edit crontab
crontab -e
```

## Next Steps

1. ✓ Setup complete! Stories will be archived automatically
2. 📊 Monitor with `python main.py --status`
3. 🐦 Check Twitter for your archived stories
4. 📝 Review `archive.json` for details
5. 🔍 Check `archiver.log` for any issues

## Support

- 📖 Full documentation: See [README.md](README.md)
- 🐛 Issues? Check the logs: `archiver.log`
- 🔑 API help: [RapidAPI](https://rapidapi.com) & [Twitter Dev](https://developer.twitter.com)
- 📚 GitHub Actions setup: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)

## Remember

- 🔐 Never share your `.env` file
- ⏱️ First run may take a few minutes
- 📱 Stories expire after 24 hours on Instagram
- 🔄 Same story won't be archived twice
- 💾 Archive data persists in `archive.json`
- ⏰ Stories uploaded today won't post until tomorrow (UTC+7)
- 🗑️ Media files are deleted after successful posting

Happy archiving! 🎉
