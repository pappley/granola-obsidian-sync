# Installation Guide - Granola Obsidian Sync

Complete step-by-step guide to install and configure the Granola Obsidian sync tool on your Mac.

## System Requirements

- **macOS**: 11 (Big Sur) or later
- **Python**: 3.9 or higher
- **Granola App**: Desktop app (macOS) installed and authenticated
- **Obsidian**: With a vault created and configured

## Prerequisites

### 1. Install Granola Desktop App

The Granola sync tool requires the Granola desktop application to be installed and authenticated on your Mac.

**Steps:**
1. Download Granola from [granola.ai](https://granola.ai)
2. Install the app (drag to Applications folder)
3. **Important**: Open the app and sign in with your account at least once
4. The authentication step creates the credentials file needed by this tool

**Where Credentials Are Stored:**
- Location: `~/Library/Application Support/Granola/supabase.json`
- This file contains your personal OAuth bearer token
- The token is used only by this tool on your local machine—it is **not** shared with anyone else
- Your token never leaves your computer (all API calls are local to your machine)

### 2. Verify Obsidian is Set Up

You need an Obsidian vault where meeting notes will be saved.

**Steps:**
1. Download Obsidian from [obsidian.md](https://obsidian.md)
2. Create a new vault or open an existing one
3. Note the vault path (you'll need this during installation)
4. Example path: `/Users/yourname/Documents/My Vault`

### 3. Install Python 3.9+

Verify Python 3.9 or higher is installed:

```bash
python3 --version
```

If Python is not installed, download from [python.org](https://www.python.org/)

## Installation

### Step 1: Download the Tool

Clone or download the `granola-obsidian-sync` repository to your Mac.

### Step 2: Run the Installer

Open Terminal and navigate to the tool directory:

```bash
cd /path/to/granola-obsidian-sync
chmod +x install.sh
./install.sh
```

### Step 3: Follow the Installation Prompts

The installer will:

1. **Verify Prerequisites**
   - Check Python version (3.9+)
   - Confirm Granola app is installed
   - Verify Granola credentials exist
   - Check for Obsidian

2. **Install Dependencies**
   - Downloads required Python packages (requests, pyyaml)

3. **Configure Your Setup**
   - Prompts for your Obsidian vault path
   - Validates the path exists
   - Generates a personalized `config.yaml` file

4. **Create Directories**
   - Creates folders for data, logs, and backups

5. **Test the Connection**
   - Runs an initial sync to verify everything works
   - Confirms your bearer token is valid

6. **Optional: Set Up Automation**
   - Offers to configure automatic syncing via cron
   - If yes: runs interactive setup to choose sync frequency

### Step 4: Verify Installation

After installation completes, check that:

1. **Configuration file created**: `config.yaml` exists in the tool directory
2. **Directories created**: `data/`, `logs/`, `backups/` folders exist
3. **Test sync succeeded**: Check the console output for success message
4. **First meeting note appeared**: Check your Obsidian vault for a test meeting file

## Configuration

### Basic Configuration

The installer creates `config.yaml` from a template. Key settings:

```yaml
paths:
  obsidian_vault: "/path/to/your/vault"  # Your vault path

sync:
  default_lookback_days: 7  # How far back to sync on first run
  update_existing_files: true  # Update notes if meeting was edited

logging:
  level: "INFO"  # Verbosity: DEBUG, INFO, WARNING, ERROR
```

### Advanced Configuration

Edit `config.yaml` to customize:

- **Sync behavior**: How often to look back, what to update, error handling
- **Output formatting**: Filename patterns, section headers, metadata fields
- **Obsidian integration**: What fields to include in frontmatter
- **Error handling**: Whether to continue on errors or stop
- **Logging**: Verbosity level and retention

See `config.yaml` for detailed explanations of all options.

## Running the Tool

### Manual Sync

Run a sync manually anytime:

```bash
python3 main.py --config config.yaml
```

### Automatic Syncing (Cron)

If you set up cron during installation, the tool will automatically sync on your configured schedule (default: every 2 hours).

**Check your cron job:**
```bash
crontab -l
```

You should see an entry like:
```
0 */2 * * * /path/to/granola-obsidian-sync/run_sync.sh
```

**View sync logs:**
```bash
ls -lah ./logs/
```

Each sync creates a timestamped log file.

## Troubleshooting

### "Granola credentials not found"

**Problem**: The installer can't find your Granola credentials.

**Solution**:
1. Open Granola app (`/Applications/Granola.app`)
2. Sign in with your account if not already signed in
3. Close the app
4. Run the installer again

**Why**: Granola stores your authentication token at `~/Library/Application Support/Granola/supabase.json` when you sign in.

### "Python 3 is not installed" or "Python 3.9 or higher required"

**Problem**: Python 3.9+ is not installed or not in your PATH.

**Solution**:
1. Check your Python version: `python3 --version`
2. If version is too old, download Python 3.9+ from [python.org](https://www.python.org/)
3. After installing, verify the new version: `python3 --version`
4. Run the installer again

### "Granola app not found"

**Problem**: The installer can't find Granola in `/Applications/`.

**Solution**:
1. Download and install Granola from [granola.ai](https://granola.ai)
2. Make sure the app is in your Applications folder
3. Run the installer again

### "API 401 error" or "Token expired"

**Problem**: The sync is failing with authentication errors.

**Solution**:
1. Open Granola app to refresh your authentication token
2. Close the app
3. Run a manual sync: `python3 main.py --config config.yaml`

The tool automatically refreshes your token on the first 401 error, but re-opening Granola ensures a fresh token is stored.

### "Vault path does not exist"

**Problem**: The path to your Obsidian vault is invalid.

**Solution**:
1. Find your Obsidian vault path:
   - Open Obsidian
   - Go to Settings → About
   - The vault location is shown (or you can see it in Finder)
2. Update the `obsidian_vault` path in `config.yaml`
3. Run a manual sync to test

### Meetings aren't syncing

**Problem**: The tool runs but no new meeting files appear in Obsidian.

**Possible causes**:
1. No new meetings since the last sync (check the log file)
2. Meetings are more than 7 days old (default lookback is 7 days; change `default_lookback_days` in `config.yaml`)
3. Granola credentials have expired (see "API 401 error" above)

**Solution**:
1. Check the most recent log file: `ls -lah ./logs/`
2. View the log: `cat ./logs/granola_sync_*.log`
3. Look for error messages or "0 documents found"
4. If the log shows "Success" but you expected files, check your vault path in `config.yaml`

### Cron job not running automatically

**Problem**: Automatic syncing isn't happening on schedule.

**Check**:
1. Verify cron job exists: `crontab -l`
2. Check recent logs: `ls -lah ./logs/ | head -5`
3. Look for error messages in the logs

**Solution**:
1. If cron job doesn't exist, run the installer again and choose to set up cron
2. Run `python3 setup_automation.py` to reconfigure cron

### Still stuck?

**Debugging steps**:
1. Run a manual sync with verbose output:
   ```bash
   python3 main.py --config config.yaml --verbose
   ```
2. Check the log file for specific error messages
3. Verify all prerequisites are installed correctly
4. Try updating `config.yaml` settings (e.g., reduce `batch_size` or increase `timeout`)

## Customization

### Change Sync Frequency

Edit your cron job:
```bash
crontab -e
```

Change the schedule line (default is `0 */2 * * *` for every 2 hours):
- `0 * * * *` - Every hour
- `0 */4 * * *` - Every 4 hours
- `0 9 * * 1-5` - Every weekday at 9 AM

### Change Lookback Period

Edit `config.yaml`:
```yaml
sync:
  default_lookback_days: 14  # Change from 7 to 14 days
```

Only affects the first sync. After that, the tool tracks the last sync time automatically.

### Customize Output Format

Edit `config.yaml` to change:
- Filename format: `filename_format: "{date}-{title}.md"`
- Section headers: `transcript_section_header: "## Transcript"`
- Frontmatter fields: add/remove fields under `obsidian.frontmatter_fields`

### Customize Error Handling

Edit `config.yaml` under `error_handling`:
```yaml
error_handling:
  continue_on_document_error: true  # Skip failed documents
  continue_on_transcript_error: true  # Create note even if transcript fails
  continue_on_mapping_error: false  # Stop if participant mapping fails
```

## Support

For help or to report issues:
1. Check this troubleshooting guide
2. Review the most recent log file in `./logs/`
3. Check the GitHub repository for known issues
4. Contact the tool maintainer

## What Happens During Sync

Here's what the tool does when it runs:

1. **Authenticate**: Loads your bearer token from Granola app data
2. **Check for new meetings**: Queries Granola API for documents since last sync
3. **Get participant info**: Looks up who was in each meeting
4. **Fetch transcripts**: Downloads full transcript content for each meeting
5. **Format notes**: Converts transcripts to markdown with speaker labels
6. **Save to Obsidian**: Writes files to your vault with YAML metadata
7. **Update timestamp**: Records sync time for next run
8. **Log results**: Writes summary to log file

## Data Privacy & Security

- **Bearer token**: Stored locally in `~/Library/Application Support/Granola/supabase.json`
- **API calls**: Made directly from your Mac to Granola's API
- **No data sharing**: Your token is never shared with anyone else
- **Local processing**: All transcript processing happens on your machine
- **Backups**: Automatic backups of mapping data stored in `./backups/`

## Next Steps

After successful installation:

1. **Monitor a sync**: Check logs in `./logs/` to see sync results
2. **Customize settings**: Edit `config.yaml` to adjust behavior
3. **Set up automation**: Run `python3 setup_automation.py` if you didn't during install
4. **Verify Obsidian**: Check that meeting notes appear in your vault
5. **Fine-tune formatting**: Adjust output format in `config.yaml` as needed

Enjoy your automated meeting transcript syncing!
