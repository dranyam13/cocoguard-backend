"""
Create password_reset_tokens table for password reset functionality
Run this script to add the table to the existing database
"""
import sqlite3
import os

# Get database path
db_path = os.path.join(os.path.dirname(__file__), 'cocoguard.db')

print(f"Database path: {db_path}")

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if table exists
cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='password_reset_tokens'
""")
table_exists = cursor.fetchone()

if table_exists:
    print("Table 'password_reset_tokens' already exists.")
else:
    print("Creating 'password_reset_tokens' table...")
    
    # Create table
    cursor.execute("""
        CREATE TABLE password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token VARCHAR(6) NOT NULL,
            email VARCHAR(255) NOT NULL,
            is_used BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create index for faster lookup
    cursor.execute("""
        CREATE INDEX idx_password_reset_email_token 
        ON password_reset_tokens (email, token, is_used)
    """)
    
    conn.commit()
    print("✅ Table 'password_reset_tokens' created successfully!")

# Verify table structure
cursor.execute("PRAGMA table_info(password_reset_tokens)")
columns = cursor.fetchall()
print("\nTable structure:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
print("\nDone!")
