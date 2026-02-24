"""
Migration script to add admin response columns to feedback table.
Run this script to add the new columns for admin feedback responses.
"""
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_config():
    """Get database configuration from environment"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'cocoguard')
    }


def add_feedback_response_columns():
    """Add admin_response, admin_response_by, and responded_at columns to feedback table"""
    config = get_db_config()
    
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        print("🔧 Adding admin response columns to feedback table...")
        
        # Check if columns already exist
        cursor.execute("SHOW COLUMNS FROM feedback LIKE 'admin_response'")
        if cursor.fetchone():
            print("✓ Column 'admin_response' already exists")
        else:
            cursor.execute("""
                ALTER TABLE feedback 
                ADD COLUMN admin_response TEXT NULL
            """)
            print("✓ Added 'admin_response' column")
        
        cursor.execute("SHOW COLUMNS FROM feedback LIKE 'admin_response_by'")
        if cursor.fetchone():
            print("✓ Column 'admin_response_by' already exists")
        else:
            cursor.execute("""
                ALTER TABLE feedback 
                ADD COLUMN admin_response_by INT NULL,
                ADD CONSTRAINT fk_feedback_responder 
                    FOREIGN KEY (admin_response_by) REFERENCES users(id) ON DELETE SET NULL
            """)
            print("✓ Added 'admin_response_by' column with foreign key")
        
        cursor.execute("SHOW COLUMNS FROM feedback LIKE 'responded_at'")
        if cursor.fetchone():
            print("✓ Column 'responded_at' already exists")
        else:
            cursor.execute("""
                ALTER TABLE feedback 
                ADD COLUMN responded_at TIMESTAMP NULL
            """)
            print("✓ Added 'responded_at' column")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show current feedback table structure
        print("\n📋 Current feedback table structure:")
        cursor.execute("DESCRIBE feedback")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("Feedback Admin Response Migration")
    print("=" * 50)
    add_feedback_response_columns()
