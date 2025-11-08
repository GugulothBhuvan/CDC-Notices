# ERP Notices Monitor

Automated monitoring system that detects new notices from IIT KGP ERP and instantly emails them to a Google Group.

## Features

- ✅ **Real-time monitoring** - Checks for new notices every 5 minutes (configurable)
- ✅ **Instant email notifications** - Sends emails to Google Group when new notices are detected
- ✅ **Duplicate prevention** - Uses database to track seen notices, only sends new ones
- ✅ **Automatic tracking** - No manual intervention needed
- ✅ **Cloud-ready** - Can run on any server/cloud platform

## Prerequisites

1. Python 3.10+ installed
2. Your ERP cookie string
3. Gmail account with App Password
4. Google Group email address

## Quick Start

### 1. Install Dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
ERP_COOKIE=JSESSIONID=...; ssoToken=...; ...
EMAIL_USER=youremail@gmail.com
EMAIL_PASS=your_16_character_app_password
GOOGLE_GROUP_EMAIL=your-group@googlegroups.com
POLL_INTERVAL=300
```

### 3. Run the Monitor

```powershell
python monitor_notices.py
```

**On First Run:**
- Loads all existing notices into database (NO emails sent)
- From now on, only NEW notices trigger emails

**On Subsequent Runs:**
- Checks for new notices every 5 minutes
- Emails ONLY new notices to Google Group

## Getting Your Cookie String

1. Open ERP Notice page: `https://erp.iitkgp.ac.in/TrainingPlacementSSO/Notice.jsp`
2. Press **F12** → **Network** tab
3. Refresh page (F5)
4. Find `ERPMonitoring.htm` request
5. Copy **Cookie** value from Request Headers

## Setting Up Google Group

1. Go to [Google Groups](https://groups.google.com)
2. Create a new group or use existing one
3. Copy the group email address
4. Add it to `.env` as `GOOGLE_GROUP_EMAIL`

## Running Automatically

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task → "When computer starts"
3. Action: Start program → `python.exe`
4. Arguments: `monitor_notices.py`
5. Start in: Your project folder
6. Check "Run whether user is logged on or not"

### Cloud Hosting

See `MONITORING_SETUP.md` for:
- Railway.app setup
- PythonAnywhere setup
- AWS EC2 setup
- Other cloud options

## Configuration

### Poll Interval

Set `POLL_INTERVAL` in `.env` (in seconds):
- `60` = Check every 1 minute
- `300` = Check every 5 minutes (recommended)
- `600` = Check every 10 minutes

### Number of Notices to Check

Edit `monitor_notices.py`:
```python
PARAMS = {
    "rows": "100",  # Change this number
    ...
}
```

## Database Management

### Re-initialize Database

If you need to reset and reload all current notices:

```powershell
python reinitialize_database.py
```

This will:
- Fetch all current notices
- Update database
- No emails sent (only new notices after this will trigger emails)

### Check Database Contents

The monitor creates `notices.db` (SQLite) to track:
- Notice IDs
- First seen timestamp
- Last seen timestamp
- Notice metadata

## Troubleshooting

### Emails not being sent

1. Check Google Group settings (allow external senders or add EMAIL_USER as member)
2. Verify Gmail App Password (not regular password)
3. Check `.env` file has all required variables

### Cookie expired

- Re-login to ERP, copy fresh cookie
- Update `ERP_COOKIE` in `.env` file
- Restart monitor

### Monitor not detecting new notices

- Run `python reinitialize_database.py` to refresh database
- Check `notices.db` file exists and is being updated
- Verify cookie is still valid

## Files

- `monitor_notices.py` - Main monitoring script
- `reinitialize_database.py` - Utility to reset/refresh database
- `requirements.txt` - Python dependencies
- `MONITORING_SETUP.md` - Detailed setup and automation guide
- `.gitignore` - Excludes secrets and generated files

## Security Notes

- **Never commit `.env` file** to version control
- Cookie strings expire - refresh periodically
- Gmail App Passwords can be revoked and regenerated
- Database file (`notices.db`) contains notice metadata

## Support

For detailed setup instructions, see `MONITORING_SETUP.md`

For cloud hosting options, see the automation section in `MONITORING_SETUP.md`
