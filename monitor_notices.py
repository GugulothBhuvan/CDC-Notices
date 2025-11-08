# monitor_notices.py - Monitor ERP notices and email new ones to Google Group
# Run: python monitor_notices.py

import os
import time
import sqlite3
import requests
import xml.etree.ElementTree as ET
from email.message import EmailMessage
import smtplib
from datetime import datetime
from dotenv import load_dotenv
import hashlib

load_dotenv()

# Configuration
AJAX_URL = "https://erp.iitkgp.ac.in/TrainingPlacementSSO/ERPMonitoring.htm"
PARAMS = {
    "action": "fetchData",
    "jqqueryid": "54",
    "_search": "false",
    "rows": "100",  # Check top 100 notices (increase to catch more)
    "page": "1",
}

# Email settings
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("EMAIL_USER")
SMTP_PASS = os.getenv("EMAIL_PASS")
GOOGLE_GROUP_EMAIL = os.getenv("GOOGLE_GROUP_EMAIL")  # e.g., your-group@googlegroups.com

# Monitoring settings
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))  # Check every 5 minutes (300 seconds)
DB_FILE = "notices.db"

# Cookie
COOKIE_HEADER = os.getenv("ERP_COOKIE")

if not COOKIE_HEADER:
    print("❌ ERROR: ERP_COOKIE environment variable not set")
    print("For local: Create .env file or set environment variable")
    print("For Railway: Set ERP_COOKIE in Railway dashboard → Variables tab")
    exit(1)

if not SMTP_USER or not SMTP_PASS:
    print("❌ ERROR: EMAIL_USER and EMAIL_PASS environment variables not set")
    print("For local: Create .env file or set environment variables")
    print("For Railway: Set EMAIL_USER and EMAIL_PASS in Railway dashboard → Variables tab")
    exit(1)

if not GOOGLE_GROUP_EMAIL:
    print("❌ ERROR: GOOGLE_GROUP_EMAIL environment variable not set")
    print("For local: Create .env file or set environment variable")
    print("For Railway: Set GOOGLE_GROUP_EMAIL in Railway dashboard → Variables tab")
    exit(1)


def init_database():
    """Initialize SQLite database to track seen notices."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS seen_notices (
            notice_id TEXT PRIMARY KEY,
            notice_hash TEXT,
            title TEXT,
            category TEXT,
            priority TEXT,
            company TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"✓ Database initialized: {DB_FILE}")


def is_first_run():
    """Check if this is the first run (database is empty)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM seen_notices")
    count = c.fetchone()[0]
    conn.close()
    return count == 0


def initialize_existing_notices():
    """Populate database with existing notices without sending emails."""
    print("\n" + "=" * 60)
    print("First Run Detected - Initializing Database")
    print("=" * 60)
    print("Loading existing notices into database...")
    print("(No emails will be sent for existing notices)")
    
    data = fetch_notices()
    if not data or "rows" not in data:
        print("⚠ Could not fetch notices for initialization")
        return False
    
    count = 0
    notice_ids = []
    for row in data["rows"]:
        if isinstance(row, dict) and "notice" in row:
            notice = row["notice"]
        elif isinstance(row, dict) and "cell" in row:
            cells = row["cell"]
            notice = {
                "id": cells[0] if len(cells) > 0 else "",
                "category": cells[1] if len(cells) > 1 else "",
                "priority": cells[2] if len(cells) > 2 else "",
                "company": cells[3] if len(cells) > 3 else "",
                "title": cells[4] if len(cells) > 4 else "",
                "description": cells[4] if len(cells) > 4 else "",
            }
        else:
            continue
        
        notice_id = str(notice.get("id", "")).strip()
        if not notice_id or notice_id == "":
            continue
        
        notice_hash = get_notice_hash(notice)
        mark_notice_seen(notice_id, notice_hash, notice)
        notice_ids.append(notice_id)
        count += 1
    
    if notice_ids:
        try:
            # Show ID range
            numeric_ids = [int(id) for id in notice_ids if id.isdigit()]
            if numeric_ids:
                print(f"✓ Notice ID range: {min(numeric_ids)} to {max(numeric_ids)}")
        except:
            pass
    
    print(f"✓ Initialized database with {count} existing notices")
    print("✓ From now on, only NEW notices will trigger emails")
    print("=" * 60)
    return True


def get_notice_hash(notice_data):
    """Generate a hash for a notice to detect changes."""
    # Use ID, title, and company to create unique hash
    key = f"{notice_data.get('id', '')}_{notice_data.get('title', '')}_{notice_data.get('company', '')}"
    return hashlib.md5(key.encode()).hexdigest()


def fetch_notices():
    """Fetch notices from ERP endpoint."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": COOKIE_HEADER,
        "Referer": "https://erp.iitkgp.ac.in/TrainingPlacementSSO/Notice.jsp"
    }
    
    try:
        r = requests.get(AJAX_URL, params=PARAMS, headers=headers, timeout=20)
        r.raise_for_status()
        
        # Try JSON first
        try:
            return r.json()
        except ValueError:
            # Parse XML
            root = ET.fromstring(r.text)
            result = {"rows": []}
            for row in root.findall('.//row'):
                cells = []
                for cell in row.findall('cell'):
                    cell_text = cell.text if cell.text else ""
                    cells.append(cell_text.strip())
                
                # Extract notice data (adjust indices based on your CSV structure)
                notice = {
                    "id": cells[0] if len(cells) > 0 else "",
                    "category": cells[1] if len(cells) > 1 else "",
                    "priority": cells[2] if len(cells) > 2 else "",
                    "company": cells[3] if len(cells) > 3 else "",
                    "title": cells[4] if len(cells) > 4 else "",
                    "description": cells[4] if len(cells) > 4 else "",  # Full description
                }
                result["rows"].append({"cell": cells, "notice": notice})
            
            return result
            
    except Exception as e:
        print(f"Error fetching notices: {e}")
        return None


def get_seen_notice_ids():
    """Get all seen notice IDs from database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT notice_id, notice_hash FROM seen_notices")
    seen = {}
    for row in c.fetchall():
        # Ensure notice_id is stored as string for consistent comparison
        notice_id = str(row[0]).strip()
        seen[notice_id] = row[1]
    conn.close()
    return seen


def mark_notice_seen(notice_id, notice_hash, notice_data):
    """Mark a notice as seen in the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if notice already exists
    c.execute("SELECT notice_id FROM seen_notices WHERE notice_id = ?", (notice_id,))
    exists = c.fetchone()
    
    if exists:
        # Update last_seen timestamp
        c.execute('''
            UPDATE seen_notices 
            SET last_seen = CURRENT_TIMESTAMP, notice_hash = ?
            WHERE notice_id = ?
        ''', (notice_hash, notice_id))
    else:
        # Insert new notice
        c.execute('''
            INSERT INTO seen_notices 
            (notice_id, notice_hash, title, category, priority, company)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            notice_id,
            notice_hash,
            notice_data.get('title', '')[:200],  # Truncate long titles
            notice_data.get('category', ''),
            notice_data.get('priority', ''),
            notice_data.get('company', '')
        ))
    
    conn.commit()
    conn.close()


def format_notice_email(notice):
    """Format a notice for email."""
    title = notice.get('title', 'No Title')
    # Clean HTML tags from title
    import re
    title = re.sub(r'<[^>]+>', '', title)
    title = title.replace('&nbsp;', ' ').strip()
    
    category = notice.get('category', 'N/A')
    priority = notice.get('priority', 'N/A')
    company = notice.get('company', 'N/A')
    notice_id = notice.get('id', 'N/A')
    description = notice.get('description', '')
    
    # Clean description
    description = re.sub(r'<[^>]+>', '', description)
    description = description.replace('&nbsp;', ' ').strip()
    
    email_body = f"""
New ERP Notice Detected!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Notice ID: {notice_id}
Category: {category}
Priority: {priority}
Company: {company}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: {title}

Description:
{description[:500]}{'...' if len(description) > 500 else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
View full notice: https://erp.iitkgp.ac.in/TrainingPlacementSSO/Notice.jsp
Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return email_body, title


def send_notice_email(notice):
    """Send email notification about a new notice to Google Group."""
    email_body, title = format_notice_email(notice)
    
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = GOOGLE_GROUP_EMAIL
    msg["Subject"] = f"[ERP Notice] {notice.get('category', 'NOTICE')} - {notice.get('company', 'New Notice')}"
    msg.set_content(email_body)
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def check_for_new_notices(send_emails=True):
    """Check for new notices and send emails.
    
    Args:
        send_emails: If False, only update database without sending emails
    """
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for new notices...")
    
    data = fetch_notices()
    if not data or "rows" not in data:
        print("⚠ No data received or invalid response")
        return 0
    
    seen_notices = get_seen_notice_ids()
    new_count = 0
    
    for row in data["rows"]:
        if isinstance(row, dict) and "notice" in row:
            notice = row["notice"]
        elif isinstance(row, dict) and "cell" in row:
            # Extract from cell array
            cells = row["cell"]
            notice = {
                "id": cells[0] if len(cells) > 0 else "",
                "category": cells[1] if len(cells) > 1 else "",
                "priority": cells[2] if len(cells) > 2 else "",
                "company": cells[3] if len(cells) > 3 else "",
                "title": cells[4] if len(cells) > 4 else "",
                "description": cells[4] if len(cells) > 4 else "",
            }
        else:
            continue
        
        notice_id = str(notice.get("id", "")).strip()
        if not notice_id or notice_id == "":
            continue
        
        notice_hash = get_notice_hash(notice)
        
        # Check if this is a new notice (not in database)
        # Normalize notice_id to string for comparison
        is_new = notice_id not in seen_notices
        
        if is_new:
            print(f"  🆕 New notice detected: ID {notice_id} - {notice.get('company', 'N/A')}")
            
            # Only send email if send_emails is True (not during initialization)
            if send_emails:
                if send_notice_email(notice):
                    print(f"  ✓ Email sent to {GOOGLE_GROUP_EMAIL}")
                    new_count += 1
                else:
                    print(f"  ✗ Failed to send email")
            else:
                print(f"  ✓ Notice added to database (no email sent)")
        
        # Mark as seen (update or insert) - always update database
        mark_notice_seen(notice_id, notice_hash, notice)
    
    if send_emails:
        if new_count == 0:
            print(f"  ✓ No new notices (checked {len(data['rows'])} notices)")
        else:
            print(f"  ✓ Sent {new_count} new notice(s) to Google Group")
    
    return new_count


def main():
    """Main monitoring loop."""
    print("=" * 60)
    print("ERP Notices Monitor - Google Group Notifier")
    print("=" * 60)
    print(f"Google Group: {GOOGLE_GROUP_EMAIL}")
    print(f"Poll Interval: {POLL_INTERVAL} seconds ({POLL_INTERVAL/60:.1f} minutes)")
    print(f"Database: {DB_FILE}")
    print("=" * 60)
    
    init_database()
    
    # On first run, initialize database with existing notices (no emails)
    if is_first_run():
        if not initialize_existing_notices():
            print("⚠ Failed to initialize. Exiting.")
            return
        print("\n✓ Initialization complete. Starting monitoring...")
    else:
        # Check how many notices are in database
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM seen_notices")
        count = c.fetchone()[0]
        conn.close()
        print(f"\n✓ Database contains {count} tracked notices")
        print("✓ Only NEW notices will trigger emails\n")
    
    print("Starting monitoring... (Press Ctrl+C to stop)")
    print(f"Will check for new notices every {POLL_INTERVAL} seconds\n")
    
    try:
        while True:
            check_for_new_notices(send_emails=True)
            print(f"\nWaiting {POLL_INTERVAL} seconds until next check...")
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        print("=" * 60)


if __name__ == "__main__":
    main()

