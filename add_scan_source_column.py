"""
Add source column to scans table.
This column tracks whether a scan came from image detection or survey assessment.

Run: python add_scan_source_column.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def add_source_column():
    with engine.connect() as conn:
        # Check if column already exists (works for both SQLite and MySQL)
        try:
            result = conn.execute(text("PRAGMA table_info(scans)"))
            columns = [row[1] for row in result.fetchall()]
            if 'source' in columns:
                print("[INFO] 'source' column already exists in scans table.")
                return
        except Exception:
            # Fallback for MySQL
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) as cnt FROM information_schema.columns 
                    WHERE table_name = 'scans' AND column_name = 'source'
                """))
                row = result.fetchone()
                if row and row[0] > 0:
                    print("[INFO] 'source' column already exists in scans table.")
                    return
            except Exception:
                pass
        
        # Add column (VARCHAR works for both SQLite and MySQL)
        conn.execute(text("""
            ALTER TABLE scans 
            ADD COLUMN source VARCHAR(10) DEFAULT 'image'
        """))
        conn.commit()
        print("[SUCCESS] Added 'source' column to scans table.")
        print("  - Default value: 'image'")
        print("  - Values: 'image' (camera scan) or 'survey' (questionnaire)")

if __name__ == "__main__":
    add_source_column()
