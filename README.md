# Granola Obsidian Sync

Automatically sync meeting transcripts from Granola to your Obsidian vault every 2 hours.

## Quick Start

**Prerequisites**: Granola app (installed & authenticated), Python 3.9+, Obsidian vault

**Installation** (3 steps):
```bash
git clone <repo-url>
cd granola-obsidian-sync
./install.sh
```

The installer will:
- ✅ Verify prerequisites (Granola, Python, Obsidian)
- ✅ Install Python dependencies
- ✅ Prompt for your Obsidian vault path
- ✅ Run a test sync to verify everything works
- ✅ Optionally set up automatic syncing via cron

**After installation**: Check your Obsidian vault for synced meeting notes (updated every 2 hours).

**For detailed setup help**: See [INSTALL.md](INSTALL.md)

---

## ⚠️ Important: API Usage

**This tool uses Granola's internal/private API endpoints**, not an official public API. Granola does not currently offer a public API ([source](https://help.granola.ai/article/feature-requests)).

**How it works:**
- Uses your personal authentication token from the Granola desktop app
- Calls the same internal API endpoints that Granola's own applications use
- Endpoints documented through community reverse-engineering efforts ([reverse-engineering-granola-api](https://github.com/getprobo/reverse-engineering-granola-api))

**What this means:**
- ✅ Works reliably with your personal Granola account
- ✅ Fetches complete meeting transcripts via API (verified: full transcript data)
- ⚠️ Not officially supported - API could change without notice
- ⚠️ Requires Granola desktop app to be installed and authenticated

**API Endpoints Used:**
- `POST https://api.granola.ai/v2/get-documents` - Fetch document metadata
- `POST https://api.granola.ai/v2/get-document-lists` - Fetch meeting series
- `POST https://api.granola.ai/v1/get-document-transcript` - Fetch full transcript content

**Authentication:** Bearer token from `~/Library/Application Support/Granola/supabase.json`

## How It Works

**Initial Setup** (one-time):
1. Install Granola desktop app and authenticate
2. Run the installer script
3. Provide your Obsidian vault path
4. Start receiving synced transcripts

**Automatic Syncing** (ongoing):
- Runs every 2 hours via cron
- Fetches new/updated meetings from Granola API
- Identifies speakers and participants
- Creates formatted markdown notes in your vault
- Logs all activity for troubleshooting

**Manual Sync** (anytime):
```bash
python3 main.py --config config.yaml
```

## New Architecture

### 📁 **Package Structure**
```
tools/granola/
├── granola_sync/        # Sync package (consolidated)
│   ├── __init__.py      # Package exports
│   ├── config.py        # Configuration management
│   ├── api.py           # Granola API client
│   ├── participants.py  # Participant detection
│   ├── obsidian.py      # Obsidian note creation
│   └── sync.py          # Main sync orchestration
├── main.py              # Main entry point
├── config.yaml          # Central configuration
├── run_sync.sh          # Automation wrapper
└── ...
```

### ⚙️ **Configuration**
- **`tools/granola/config.yaml`** - Centralized configuration
- **Automatic validation** - Config validation on startup
- **Environment variables** - Support for config overrides
- **Path management** - Smart path resolution and directory creation

### 🔄 **Smart Features**
- **Auto-refresh mapping** - Document mappings refresh when stale (24h default)
- **Enhanced participant detection** - Better speaker identification logic
- **Data validation** - API response validation with graceful fallback
- **Comprehensive error handling** - Configurable continue-on-error behavior
- **Backup system** - Automatic backups of critical data

### 📊 **Monitoring & Logging**
- **Detailed statistics** - Success rates, processing counts, timing
- **Structured logging** - Configurable log levels and formatting
- **Status reporting** - Clear success/failure reporting
- **Performance metrics** - Duration tracking and throughput stats

## Configuration Highlights

### Key Settings in `tools/granola/config.yaml`:
```yaml
# Smart data management
data:
  mapping_max_age_hours: 24
  auto_refresh_mapping: true
  validate_api_responses: true

# Enhanced error handling  
error_handling:
  continue_on_document_error: true
  retry_exponential_backoff: true
  retry_max_delay: 60.0

# Development/testing
development:
  dry_run: false
  verbose_output: false
```

## What's Improved

### ✅ **Code Organization**
- **Single responsibility** - Each module has a focused purpose
- **Clean interfaces** - Well-defined APIs between components
- **Removed duplication** - Consolidated 10+ scripts into focused modules
- **Configuration-driven** - Behavior controlled via config, not code

### ✅ **Reliability** 
- **Smart mapping refresh** - No more stale participant data
- **Better error handling** - Graceful degradation and recovery
- **Data validation** - Prevents corrupt data from breaking sync
- **Backup systems** - Protection against data loss

### ✅ **Performance**
- **Efficient API usage** - Smarter request patterns and caching
- **Reduced redundancy** - Skip unnecessary operations
- **Better resource management** - Proper cleanup and memory usage

### ✅ **Maintainability**
- **Modular design** - Easy to modify individual components
- **Comprehensive logging** - Better debugging and monitoring
- **Clear configuration** - Easy to adjust behavior without code changes
- **Type hints & documentation** - Self-documenting code

## Migration from v1.x

The new system is **fully backward compatible** with existing:
- ✅ Obsidian vault structure and file formats
- ✅ Document mappings and participant data
- ✅ Cron job scheduling (just uses new main script)
- ✅ Log file locations and formats

## File Status

### 🗂️ **Active Files**
- `tools/granola/main.py` - Main entry point
- `tools/granola/config.yaml` - Central configuration
- `tools/granola/granola_sync/` - Package modules (consolidated)
- `tools/granola/run_sync.sh` - Automation wrapper
- `tools/granola/setup_automation.py` - Cron setup tool
- `tools/granola/data/` - Document mapping and data files
- `tools/granola/logs/` - Sync logs
- `tools/granola/backups/` - Automatic backups

### 🔄 **Current Automation**
- **Cron schedule**: Every 2 hours
- **Script**: `tools/granola/run_sync.sh`
- **Logs**: `tools/granola/logs/granola_sync_TIMESTAMP.log`

---

*System successfully refactored on 2025-09-09*
*File organization improved on 2025-11-21*