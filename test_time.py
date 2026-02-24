import sqlite3
from datetime import datetime

conn = sqlite3.connect('C:/xampp/htdocs/cocoguard-backend/cocoguard.db')
cur = conn.cursor()

# Test what SQLite's CURRENT_TIMESTAMP returns
cur.execute("SELECT CURRENT_TIMESTAMP")
sqlite_now = cur.fetchone()[0]

# Test what datetime('now') returns  
cur.execute("SELECT datetime('now')")
sqlite_now_utc = cur.fetchone()[0]

# Test what datetime('now', 'localtime') returns
cur.execute("SELECT datetime('now', 'localtime')")
sqlite_now_local = cur.fetchone()[0]

print(f"SQLite CURRENT_TIMESTAMP: {sqlite_now}")
print(f"SQLite datetime('now'):   {sqlite_now_utc}")
print(f"SQLite datetime('now', 'localtime'): {sqlite_now_local}")
print(f"Python datetime.now():    {datetime.now()}")

conn.close()
