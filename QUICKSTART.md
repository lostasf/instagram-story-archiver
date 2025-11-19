# Quick Start Guide

Get the Instagram Story Archiver running in 3 minutes using GitHub Actions! 🚀

## Option 1: GitHub Actions (Recommended) ⭐

No local setup required - runs automatically every hour!

### 1. Fork Repository (30 seconds)

Click the "Fork" button to create your own copy.

### 2. Add Secrets (1 minute)

Go to **Settings → Secrets and variables → Actions**

Add these **Secrets**:
```
RAPIDAPI_KEY=your_key
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

Add this **Variable**:
```
INSTAGRAM_USERNAME=jkt48.gendis
```

### 3. Done! ✅

Go to **Actions** tab and watch it run automatically every hour.

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

### 4. Run Once

```bash
python main.py
```

## Common Commands

### Run once and exit
```bash
python main.py --once
```

### Archive specific story
```bash
python main.py --story-id 2921414441985452983
```

### View archive statistics
```bash
python main.py --status
```

### View logs in real-time
```bash
tail -f archiver.log
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

1. ✓ Connects to Instagram API
2. ✓ Fetches stories from jkt48.gendis
3. ✓ Downloads media files
4. ✓ Compresses images if needed
5. ✓ Posts to Twitter as thread
6. ✓ Records in archive.json
7. ✓ Cleans up temporary files

Takes 1-3 minutes per story depending on media size.

## Monitoring

Check these files to monitor progress:

```bash
# Application logs (live updates)
tail -f archiver.log

# Archive database (story tracking)
cat archive.json

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
# Increase check interval in .env
CHECK_INTERVAL_HOURS=2
```

### "Authentication failed"
```bash
# Verify credentials in .env are correct
python test_setup.py
```

## What Gets Archived?

Each story becomes a Twitter thread:

- **Tweet 1**: Story intro with media count
- **Tweets 2+**: Individual images/videos
- **Last Tweet**: Completion message

All tracked in `archive.json` with:
- Story ID
- Timestamp
- Media count
- Tweet IDs
- Original URLs

## Rate Limits

⚠️ Be aware of these limits:

| Service | Limit | Duration |
|---------|-------|----------|
| Instagram API | 1000 | Per month |
| Twitter Media Upload | 1500 | Per 15 minutes |
| Default Check Interval | 1 hour | Configurable |

**Estimated Usage**: 
- ~12 requests/day at 1-hour intervals
- ~360 requests/month (well under 1000 limit)
- Plenty of room for multiple accounts

## Advanced Usage

### Run with custom settings

```bash
# 1. Edit .env
INSTAGRAM_USERNAME=different_user
CHECK_INTERVAL_HOURS=6

# 2. Run
python main.py
```

### Run in background (Linux/Mac)

```bash
# Start in background
nohup python main.py > archiver.log 2>&1 &

# Stop later
pkill -f "python main.py"
```

### Schedule with cron (Linux/Mac)

```bash
# Run once daily at 9 AM
0 9 * * * cd /path/to/project && python main.py --once

# Edit crontab
crontab -e
```

### Run on Windows (PowerShell)

```powershell
# Run in background
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden

# Run in Windows Task Scheduler
# Create task: schtasks /create /tn ArchiveStories /tr "python C:\path\main.py" /sc hourly
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

## Remember

- 🔐 Never share your `.env` file
- ⏱️ First run may take a few minutes
- 📱 Stories expire after 24 hours on Instagram
- 🔄 Same story won't be archived twice
- 💾 Archive data persists in `archive.json`

Happy archiving! 🎉
