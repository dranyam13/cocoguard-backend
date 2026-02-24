"""
Add FCM token column to users table for push notifications.
Run this script to add the fcm_token column to existing databases.
"""
import sqlite3
import os

def add_fcm_token_column():
    # Connect to the database
    db_path = os.path.join(os.path.dirname(__file__), 'cocoguard.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'fcm_token' in columns:
            print("Column 'fcm_token' already exists in users table.")
            return True
        
        # Add the fcm_token column
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN fcm_token VARCHAR(512)
        """)
        
        conn.commit()
        print("Successfully added 'fcm_token' column to users table.")
        return True
        
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    add_fcm_token_column()
