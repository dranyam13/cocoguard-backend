import sqlite3
from datetime import datetime

conn = sqlite3.connect('c:/xampp/htdocs/cocoguard-backend/cocoguard.db')
cur = conn.cursor()

# Get the latest scan created_at format
cur.execute('SELECT created_at FROM scans ORDER BY id DESC LIMIT 1')
row = cur.fetchone()[0]
print(f'DB format: {repr(row)}')
print(f'Type: {type(row)}')

# Count scans today using string comparison
cur.execute('SELECT COUNT(*) FROM scans WHERE created_at >= "2026-02-05 00:00:00"')
c1 = cur.fetchone()[0]
print(f'String >= 2026-02-05 00:00:00 count: {c1}')

# Count using date() function
cur.execute('SELECT COUNT(*) FROM scans WHERE date(created_at) = "2026-02-05"')
c2 = cur.fetchone()[0]
print(f'date(created_at) = 2026-02-05 count: {c2}')

# Compare with parameterized query
start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
print(f'\nPython datetime: {start}')
print(f'Python datetime str: {str(start)}')
cur.execute('SELECT COUNT(*) FROM scans WHERE created_at >= ?', (start,))
c3 = cur.fetchone()[0]
print(f'Parameterized count: {c3}')

# Try with string
cur.execute('SELECT COUNT(*) FROM scans WHERE created_at >= ?', (str(start),))
c4 = cur.fetchone()[0]
print(f'Parameterized string count: {c4}')

conn.close()
