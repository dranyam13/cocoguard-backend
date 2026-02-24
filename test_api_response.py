"""Test the notifications API response format"""
import sys
sys.path.insert(0, 'C:/xampp/htdocs/cocoguard-backend')

from app.utils.timezone import to_manila_iso
from datetime import datetime
import sqlite3

# Get a real notification timestamp from the database
conn = sqlite3.connect('C:/xampp/htdocs/cocoguard-backend/cocoguard.db')
cur = conn.cursor()
cur.execute('SELECT id, created_at FROM notifications ORDER BY id DESC LIMIT 1')
r = cur.fetchone()
conn.close()

notification_id = r[0]
db_timestamp = r[1]

# Parse the DB timestamp
dt = datetime.fromisoformat(db_timestamp)

# Convert using our function
manila_iso = to_manila_iso(dt)

print(f"Database timestamp: {db_timestamp}")
print(f"Parsed datetime: {dt}")
print(f"Manila ISO output: {manila_iso}")
print(f"Current time: {datetime.now()}")
print()

# Simulate what JavaScript would do
print("JavaScript parsing simulation:")
print(f"  new Date('{manila_iso}') would parse as local time correctly")
print(f"  Because the timezone offset +08:00 is included")
