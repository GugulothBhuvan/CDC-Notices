# ERP Notices Monitoring - Google Group Setup

This system monitors the IIT KGP ERP notices and automatically emails new notices to a Google Group instantly.

## Features

- ✅ **Real-time monitoring** - Checks for new notices every 5 minutes (configurable)
- ✅ **Instant email notifications** - Sends emails to Google Group when new notices are detected
- ✅ **Duplicate detection** - Uses database to track seen notices
- ✅ **Automatic tracking** - No manual intervention needed
- ✅ **Background service** - Can run continuously

## Setup

### 1. Create/Configure Google Group

1. Go to [Google Groups](https://groups.google.com)
2. Create a new group or use an existing one
3. Note the group email address (e.g., `your-group@googlegroups.com`)
4. Add members who should receive notices
5. Configure group settings:
   - Allow external senders (if sending from non-member account)
   - Or add your `EMAIL_USER` as a member of the group

### 2. Update .env File

Add these lines to your `.env` file:

```env
# Existing settings...
ERP_COOKIE=your_cookie_string
EMAIL_USER=youremail@gmail.com
EMAIL_PASS=your_app_password
TO_ADDRESS=your.personal@mail.com

# New settings for monitoring
GOOGLE_GROUP_EMAIL=your-group@googlegroups.com
POLL_INTERVAL=300  # Check every 300 seconds (5 minutes)
```

**Settings:**
- `GOOGLE_GROUP_EMAIL`: Your Google Group email address
- `POLL_INTERVAL`: How often to check (in seconds). Default: 300 (5 minutes)

### 3. Run the Monitor

**Option A: Run manually (for testing)**
```powershell
python monitor_notices.py
```

**Option B: Run in background (Windows)**
```powershell
# Run in background
Start-Process python -ArgumentList "monitor_notices.py" -WindowStyle Hidden
```

**Option C: Run as Windows Service (Recommended)**

See "Running as Service" section below.

## How It Works

1. **First Run**: 
   - Detects empty database
   - Fetches all existing notices from ERP
   - Populates database with existing notices
   - **NO emails are sent** for existing notices
   
2. **Subsequent Runs**:
   - Polling: Checks ERP endpoint every X seconds (default: 5 minutes)
   - Detection: Compares new notices with database to find new ones
   - Email: Sends formatted email to Google Group **ONLY for new notices**
   - Tracking: Stores all notices in database to prevent duplicate emails

**Important**: Only notices that appear AFTER the first run will trigger emails. This prevents spamming your Google Group with old notices.

## Email Format

Each new notice is sent as an email with:
- Subject: `[ERP Notice] {Category} - {Company}`
- Body: Formatted notice details
- Includes: Notice ID, Category, Priority, Company, Title, Description

## Database

The script creates `notices.db` (SQLite) to track:
- Notice IDs
- Notice hashes (to detect changes)
- First seen timestamp
- Last seen timestamp
- Notice metadata (title, category, priority, company)

## Configuration

### Poll Interval

Adjust `POLL_INTERVAL` in `.env`:
- `60` = Check every 1 minute (more frequent, more API calls)
- `300` = Check every 5 minutes (recommended)
- `600` = Check every 10 minutes (less frequent)

### Number of Notices to Check

Edit `monitor_notices.py`:
```python
PARAMS = {
    "rows": "50",  # Change this number
    ...
}
```

## Running as Windows Service

### Method 1: Task Scheduler (Recommended)

1. Open **Task Scheduler**
2. Create Basic Task → Name: "ERP Notices Monitor"
3. Trigger: **When the computer starts**
4. Action: **Start a program**
5. Program: `C:\Python313\python.exe` (or your Python path)
6. Arguments: `C:\Users\bhuva\OneDrive\Desktop\erp-notices\monitor_notices.py`
7. Start in: `C:\Users\bhuva\OneDrive\Desktop\erp-notices`
8. Check "Run whether user is logged on or not"
9. Finish

### Method 2: NSSM (Non-Sucking Service Manager)

1. Download [NSSM](https://nssm.cc/download)
2. Install as service:
```powershell
nssm install ERPN noticesMonitor "C:\Python313\python.exe" "C:\Users\bhuva\OneDrive\Desktop\erp-notices\monitor_notices.py"
nssm set ERPN noticesMonitor AppDirectory "C:\Users\bhuva\OneDrive\Desktop\erp-notices"
nssm start ERPN noticesMonitor
```

## Troubleshooting

### Emails not being sent

1. **Check Google Group settings:**
   - Ensure group allows external senders
   - Or add `EMAIL_USER` as a group member

2. **Check email credentials:**
   - Verify `EMAIL_PASS` is an App Password (not regular password)
   - Test with `python test_email.py`

3. **Check logs:**
   - Run monitor in foreground to see output
   - Check for error messages

### Duplicate emails

- The database tracks notices by ID
- If you see duplicates, the notice ID might have changed
- Reset database: `python reset_database.py` (will re-initialize on next run)

### Want to start fresh?

If you want to reset the database and re-initialize:
```powershell
python reset_database.py
```
This will delete the database. On next run, it will re-initialize with current notices (no emails) and then only send emails for truly new notices.

### Cookie expired

- The monitor will fail when cookie expires
- Re-login to ERP, copy fresh cookie, update `.env`
- Or use Selenium-based approach for automatic cookie refresh

## Testing

1. **Test email to group:**
   ```powershell
   python test_email.py
   ```
   (Update `TO_ADDRESS` in `.env` to your group email temporarily)

2. **Test monitoring (dry run):**
   - Run `python monitor_notices.py`
   - Let it check once
   - Stop with Ctrl+C
   - Check if database was created

3. **Test with new notice:**
   - Wait for a new notice to appear on ERP
   - Monitor should detect and email it

## Monitoring Status

The script prints status messages:
- `🆕 New notice detected` - Found a new notice
- `✓ Email sent` - Successfully sent email
- `✓ No new notices` - Checked, nothing new
- `⚠ No data received` - API error

## Stopping the Monitor

- If running in terminal: Press `Ctrl+C`
- If running as service: Stop via Task Scheduler or Services
- If running in background: Find process and kill it

## Database Management

**View seen notices:**
```powershell
python -c "import sqlite3; conn = sqlite3.connect('notices.db'); print(conn.execute('SELECT * FROM seen_notices ORDER BY first_seen DESC LIMIT 10').fetchall()); conn.close()"
```

**Reset database (start fresh):**
```powershell
Remove-Item notices.db
python monitor_notices.py  # Will create new database
```

## Security Notes

- Keep `.env` file secure (never commit to git)
- Cookie expires periodically - update when needed
- Google Group email is public to group members
- Database file contains notice metadata (not sensitive)

