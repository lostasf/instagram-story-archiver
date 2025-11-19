# Installation Guide

Complete step-by-step installation instructions.

## System Requirements

- **OS**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **RAM**: 512MB minimum, 1GB recommended
- **Disk**: 500MB free (for media cache)
- **Network**: Internet connection required

## Installation

### Step 1: Verify Python Installation

```bash
python3 --version
# Should output: Python 3.8.x or higher
```

If not installed, download from [python.org](https://www.python.org/downloads/)

### Step 2: Clone/Download Project

```bash
cd ~/projects/  # or any directory you prefer
git clone <repository-url>
cd gendis-instagram-story-archiver
```

Or download ZIP from GitHub and extract.

### Step 3: Create Virtual Environment (Recommended)

```bash
# On Linux/Mac
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Your prompt should now start with `(venv)`.

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

Wait for installation to complete (~30 seconds).

Verify installation:
```bash
pip list
# Should show: requests, tweepy, python-dotenv, schedule, Pillow
```

### Step 5: Get API Keys

#### Instagram API (RapidAPI)

1. Visit [RapidAPI.com](https://rapidapi.com)
2. Sign up (free account)
3. Search for "Instagram" or use [instagram120](https://rapidapi.com/usmankhalid/api/instagram120)
4. Click "Subscribe" (select free plan)
5. Copy your API key from the dashboard
6. Host: `instagram120.p.rapidapi.com` (or your chosen API)

#### Twitter API v2

1. Visit [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new app (or use existing)
3. Go to "Keys and tokens"
4. Generate/copy:
   - API Key (Consumer Key)
   - API Secret Key (Consumer Secret)
   - Access Token
   - Access Token Secret
5. Go to "Settings" and enable OAuth 1.0a
6. From "Tokens and apps" → "App", generate Bearer Token

**Required Permissions:**
- Read and write access
- Media upload capability

### Step 6: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit with your API keys
# On Linux/Mac
nano .env
# Or use your editor: code .env, vim .env, etc.

# On Windows (Notepad)
notepad .env
```

File should look like:
```env
RAPIDAPI_KEY=your_key_here
RAPIDAPI_HOST=instagram120.p.rapidapi.com
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
INSTAGRAM_USERNAME=jkt48.gendis
CHECK_INTERVAL_HOURS=1
```

### Step 7: Verify Setup

```bash
python test_setup.py
```

Expected output:
```
============================================================
Gendis Story Archiver - Setup Test
============================================================
Testing configuration...
✓ Configuration loaded successfully
  - Instagram Username: jkt48.gendis
  - Check Interval: 1 hour(s)
  - Archive DB: ./archive.json
  - Media Cache: ./media_cache

Testing Instagram API...
✓ Instagram API initialized
✓ Successfully connected to Instagram API

Testing Twitter API...
✓ Twitter API initialized
✓ Successfully authenticated to Twitter API
  - Username: @your_twitter_handle

============================================================
✓ All tests passed! Ready to start archiving.
============================================================
```

If you see errors, check:
- API keys are correct (copy-paste carefully)
- No extra spaces in `.env`
- All required keys are present
- Internet connection is working

## Directory Structure After Installation

```
gendis-instagram-story-archiver/
├── .env                    # Your config (DO NOT share)
├── .env.example            # Template (safe to share)
├── .gitignore             # Git ignore rules
├── README.md              # Full documentation
├── QUICKSTART.md          # Quick start guide
├── INSTALLATION.md        # This file
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker container config
├── docker-compose.yml     # Docker compose config
├── main.py               # Entry point
├── config.py             # Configuration handler
├── story_archiver.py     # Core archiver
├── instagram_api.py      # Instagram API wrapper
├── twitter_api.py        # Twitter API wrapper
├── media_manager.py      # Media handler
├── archive_manager.py    # Archive database
├── test_setup.py         # Setup verification
├── archive.json          # Archive database (created on first run)
├── archiver.log          # Application logs (created on first run)
└── media_cache/          # Media cache (created on first run)
```

## Deactivating Virtual Environment

When you're done, deactivate the environment:

```bash
deactivate
```

To reactivate later:
```bash
# Linux/Mac
source venv/bin/activate

# Windows
.\venv\Scripts\Activate.ps1
```

## Installation Troubleshooting

### "pip: command not found"
```bash
# Use python3 explicitly
python3 -m pip install -r requirements.txt
```

### "ModuleNotFoundError" after installation
```bash
# Make sure virtual environment is activated
# (you should see (venv) in your prompt)
which python  # Should show path with 'venv'

# If not activated, activate it:
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows
```

### "Permission denied" on Linux/Mac
```bash
# Make main.py executable
chmod +x main.py

# Run with python explicitly
python main.py
```

### "Pillow installation fails"
```bash
# Windows users may need Microsoft C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Linux (Debian/Ubuntu)
sudo apt-get install python3-dev python3-pip libjpeg-dev zlib1g-dev

# macOS
brew install jpeg
```

### "Connection timeout" during pip install
```bash
# Try with different PyPI index
pip install -i https://pypi.org/simple/ -r requirements.txt

# Or upgrade pip first
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Docker Installation (Alternative)

Skip Python setup and use Docker instead:

### Docker Prerequisites
- Docker Desktop installed ([docker.com](https://www.docker.com/products/docker-desktop))
- Docker running

### Docker Setup

```bash
# Build and run
docker-compose up -d

# Verify
docker-compose ps

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

All configuration is passed via `.env` file - no manual setup needed inside container.

## Verification Checklist

After installation, verify:

- [ ] Python 3.8+ installed: `python --version`
- [ ] Virtual environment created and activated
- [ ] Dependencies installed: `pip list` shows all packages
- [ ] `.env` file created with all API keys
- [ ] `test_setup.py` passes all checks
- [ ] Directory structure is correct
- [ ] Permissions are correct: `ls -l main.py`

## Next Steps

Once installation is complete:

1. Read [QUICKSTART.md](QUICKSTART.md) to start using
2. Review [README.md](README.md) for full documentation
3. Run `python main.py --once` for test run
4. Start scheduler: `python main.py`
5. Monitor with: `tail -f archiver.log`

## Getting Help

If installation fails:

1. **Check logs**: `cat archiver.log` (if it exists)
2. **Verify Python**: `python --version`
3. **Verify pip**: `pip --version`
4. **Check internet**: `ping google.com`
5. **Test API keys**: `python test_setup.py`
6. **Review README.md** Troubleshooting section

## Updating

To update to latest version:

```bash
# Backup current configuration
cp .env .env.backup

# Pull latest code
git pull

# Update dependencies
pip install --upgrade -r requirements.txt

# Test
python test_setup.py
```

## Uninstalling

To remove everything:

```bash
# Deactivate virtual environment
deactivate

# Remove project directory
rm -rf gendis-instagram-story-archiver/

# Or just remove virtual environment
rm -rf venv/
```

Archives and logs are in the project directory, so back them up first if needed:

```bash
# Backup before deleting
cp archive.json ~/backups/archive.json.backup
```

## Production Deployment

For running on a server:

1. **Use Docker** for consistency:
   ```bash
   docker-compose up -d
   ```

2. **Use systemd service** (Linux):
   Create `/etc/systemd/system/archiver.service`:
   ```ini
   [Unit]
   Description=Gendis Story Archiver
   After=network.target

   [Service]
   Type=simple
   User=archiver
   WorkingDirectory=/home/archiver/project
   ExecStart=/home/archiver/project/venv/bin/python main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Then: `sudo systemctl enable archiver` and `sudo systemctl start archiver`

3. **Use process manager** (e.g., supervisor, PM2)

4. **Monitor with logs**: `journalctl -u archiver -f`

## Security Notes

- ✅ `.env` is in `.gitignore` (won't be committed)
- ❌ Never share `.env` file
- ✅ Rotate API keys periodically
- ❌ Don't hardcode secrets in code
- ✅ Use environment variables in production
- ❌ Don't run as root unless necessary

---

Installation complete! You're ready to start archiving stories. 🎉
