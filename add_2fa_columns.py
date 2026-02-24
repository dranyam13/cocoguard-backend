"""
Migration script to add 2FA columns to the users table
"""
import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'cocoguard.db')

def migrate():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    migrations_applied = []
    
    # Add two_factor_secret column
    if 'two_factor_secret' not in columns:
        print("Adding 'two_factor_secret' column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN two_factor_secret VARCHAR(32)")
        migrations_applied.append('two_factor_secret')
    else:
        print("Column 'two_factor_secret' already exists, skipping...")
    
    # Add two_factor_enabled column
    if 'two_factor_enabled' not in columns:
        print("Adding 'two_factor_enabled' column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0")
        migrations_applied.append('two_factor_enabled')
    else:
        print("Column 'two_factor_enabled' already exists, skipping...")
    
    conn.commit()
    
    # Verify
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print("\nCurrent users table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    conn.close()
    
    if migrations_applied:
        print(f"\n✅ Migration complete! Added columns: {', '.join(migrations_applied)}")
    else:
        print("\n✅ No migrations needed - all columns already exist")

if __name__ == "__main__":
    migrate()
