"""
Migration script to remove plantation_name and total_trees columns from the farms table.
SQLite doesn't support DROP COLUMN, so we need to recreate the table.
"""
import sqlite3

def migrate():
    db_path = 'c:/xampp/htdocs/cocoguard-backend/cocoguard.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("Starting migration: Remove plantation_name and total_trees from farms table...")
    
    try:
        # Step 1: Create new table without the unwanted columns
        cur.execute('''
            CREATE TABLE IF NOT EXISTS farms_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(150) NOT NULL,
                address_line VARCHAR(255),
                region VARCHAR(100),
                province VARCHAR(100),
                city VARCHAR(100),
                barangay VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Step 2: Copy data from old table
        cur.execute('''
            INSERT INTO farms_new (id, user_id, name, address_line, region, province, city, barangay, created_at, updated_at)
            SELECT id, user_id, name, address_line, region, province, city, barangay, created_at, updated_at
            FROM farms
        ''')
        
        # Step 3: Drop old table
        cur.execute('DROP TABLE farms')
        
        # Step 4: Rename new table
        cur.execute('ALTER TABLE farms_new RENAME TO farms')
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify
        cur.execute('PRAGMA table_info(farms)')
        columns = cur.fetchall()
        print("\nNew farms table columns:")
        for c in columns:
            print(f"  - {c[1]}")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
