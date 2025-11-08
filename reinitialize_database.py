# reinitialize_database.py - Re-initialize database with all current notices
# Use this to fix the database if it's missing notices
# Run: python reinitialize_database.py

import os
import sqlite3
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "notices.db"
COOKIE_HEADER = os.getenv("ERP_COOKIE")
AJAX_URL = "https://erp.iitkgp.ac.in/TrainingPlacementSSO/ERPMonitoring.htm"

if not COOKIE_HEADER:
    print("❌ ERROR: ERP_COOKIE not found in .env file")
    exit(1)

def get_notice_hash(notice_data):
    """Generate a hash for a notice."""
    import hashlib
    key = f"{notice_data.get('id', '')}_{notice_data.get('title', '')}_{notice_data.get('company', '')}"
    return hashlib.md5(key.encode()).hexdigest()

def fetch_notices():
    """Fetch notices from ERP."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": COOKIE_HEADER,
        "Referer": "https://erp.iitkgp.ac.in/TrainingPlacementSSO/Notice.jsp"
    }
    
    params = {
        "action": "fetchData",
        "jqqueryid": "54",
        "_search": "false",
        "rows": "100",  # Fetch more notices
        "page": "1",
    }
    
    try:
        r = requests.get(AJAX_URL, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        
        try:
            return r.json()
        except ValueError:
            root = ET.fromstring(r.text)
            result = {"rows": []}
            for row in root.findall('.//row'):
                cells = []
                for cell in row.findall('cell'):
                    cells.append(cell.text.strip() if cell.text else "")
                result["rows"].append({"cell": cells})
            return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def mark_notice_seen(notice_id, notice_hash, notice_data):
    """Mark a notice as seen."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT notice_id FROM seen_notices WHERE notice_id = ?", (notice_id,))
    exists = c.fetchone()
    
    if not exists:
        c.execute('''
            INSERT INTO seen_notices 
            (notice_id, notice_hash, title, category, priority, company)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            notice_id,
            notice_hash,
            notice_data.get('title', '')[:200],
            notice_data.get('category', ''),
            notice_data.get('priority', ''),
            notice_data.get('company', '')
        ))
    
    conn.commit()
    conn.close()

print("=" * 60)
print("Re-initialize Database with Current Notices")
print("=" * 60)

# Check current database
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM seen_notices")
old_count = c.fetchone()[0]
conn.close()

print(f"Current notices in database: {old_count}")

print("\nFetching current notices from ERP...")
data = fetch_notices()

if not data or "rows" not in data:
    print("❌ Failed to fetch notices")
    exit(1)

print(f"Found {len(data['rows'])} notices from ERP")

count = 0
notice_ids = []

for row in data["rows"]:
    if isinstance(row, dict) and "cell" in row:
        cells = row["cell"]
        notice = {
            "id": str(cells[0]).strip() if len(cells) > 0 else "",
            "category": cells[1] if len(cells) > 1 else "",
            "priority": cells[2] if len(cells) > 2 else "",
            "company": cells[3] if len(cells) > 3 else "",
            "title": cells[4] if len(cells) > 4 else "",
        }
    else:
        continue
    
    notice_id = notice.get("id", "")
    if not notice_id:
        continue
    
    notice_hash = get_notice_hash(notice)
    mark_notice_seen(notice_id, notice_hash, notice)
    notice_ids.append(notice_id)
    count += 1

# Get final count
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM seen_notices")
new_count = c.fetchone()[0]
conn.close()

print(f"\n✓ Processed {count} notices")
print(f"✓ Database now contains {new_count} total notices")

if notice_ids:
    try:
        numeric_ids = [int(id) for id in notice_ids if id.isdigit()]
        if numeric_ids:
            print(f"✓ Notice ID range: {min(numeric_ids)} to {max(numeric_ids)}")
    except:
        pass

print("\n" + "=" * 60)
print("Re-initialization complete!")
print("=" * 60)
print("\nNow run the monitor:")
print("  python monitor_notices.py")
print("\nOnly NEW notices (after this point) will trigger emails.")

