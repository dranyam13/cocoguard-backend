import sys
sys.path.insert(0, 'c:/xampp/htdocs/cocoguard-backend')

from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from app import models

# Connect to database
engine = create_engine('sqlite:///c:/xampp/htdocs/cocoguard-backend/cocoguard.db')
Session = sessionmaker(bind=engine)
db = Session()

# Current time values
now = datetime.utcnow()
start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

print(f"Current UTC: {now}")
print(f"Start of today UTC: {start_of_today}")
print()

# Test the exact query from analytics.py
today_scans = db.query(func.count(models.Scan.id))\
    .filter(models.Scan.created_at >= start_of_today).scalar() or 0

print(f"Today's scans (SQLAlchemy query): {today_scans}")

# Raw SQL for comparison
from sqlalchemy import text
result = db.execute(text('SELECT COUNT(*) FROM scans WHERE created_at >= :start'), {'start': str(start_of_today)})
raw_count = result.fetchone()[0]
print(f"Today's scans (raw SQL): {raw_count}")

# Check the generated SQL
from sqlalchemy.dialects import sqlite
query = db.query(func.count(models.Scan.id)).filter(models.Scan.created_at >= start_of_today)
compiled = query.statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
print(f"\nGenerated SQL: {compiled}")

db.close()
