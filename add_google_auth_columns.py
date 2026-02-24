"""
Migration script to add Google authentication columns to users table
and create registration_tokens table.
"""
import sys
sys.path.insert(0, '.')

import sqlite3

DB_PATH = "cocoguard.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add google_id column to users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)")
        print("✓ Added 'google_id' column to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("• 'google_id' column already exists")
        else:
            print(f"✗ Error adding google_id: {e}")
    
    # 2. Add auth_provider column to users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) DEFAULT 'email'")
        print("✓ Added 'auth_provider' column to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("• 'auth_provider' column already exists")
        else:
            print(f"✗ Error adding auth_provider: {e}")
    
    # 3. Create registration_tokens table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registration_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) NOT NULL,
                token VARCHAR(10) NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        print("✓ Created 'registration_tokens' table")
    except sqlite3.OperationalError as e:
        print(f"✗ Error creating registration_tokens table: {e}")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
