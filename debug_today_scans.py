import sys
sys.path.insert(0, 'c:/xampp/htdocs/cocoguard-backend')

from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, and_, text
from sqlalchemy.orm import sessionmaker
from app import models

# Connect directly to db
engine = create_engine('sqlite:///c:/xampp/htdocs/cocoguard-backend/cocoguard.db')
Session = sessionmaker(bind=engine)
db = Session()

# Replicate exact logic from analytics.py
now = datetime.utcnow()
start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

print(f"Current UTC time: {now}")
print(f"Start of today (UTC): {start_of_today}")
print()

# Query today's scans
today_scans_query = db.query(func.count(models.Scan.id)).filter(models.Scan.created_at >= start_of_today)

# Print the actual SQL
from sqlalchemy.dialects import sqlite
compiled = today_scans_query.statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
print(f"SQL Query: {compiled}")
print()

# Execute
today_scans = today_scans_query.scalar() or 0
print(f"Today's scans count: {today_scans}")

# Now check scans manually  
result = db.execute(text("SELECT created_at FROM scans ORDER BY id DESC LIMIT 5"))
print("\nLatest 5 scan timestamps:")
for row in result:
    print(f"  {row[0]}")

# Test with local time
start_of_today_local = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
print(f"\nStart of today (LOCAL): {start_of_today_local}")
local_query = db.query(func.count(models.Scan.id)).filter(models.Scan.created_at >= start_of_today_local)
local_count = local_query.scalar() or 0
print(f"Count with local start: {local_count}")

db.close()
