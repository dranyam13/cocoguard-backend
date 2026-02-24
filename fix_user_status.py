"""Fix user status values in database"""
import sqlite3

conn = sqlite3.connect('cocoguard.db')
cursor = conn.cursor()

# Check current status values
print("Current user statuses:")
cursor.execute("SELECT id, username, status FROM users")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} -> status: '{row[2]}'")

# Update any NULL, empty, or 'pending' status to 'active'
cursor.execute("""
    UPDATE users 
    SET status = 'active' 
    WHERE status IS NULL 
       OR status = '' 
       OR LOWER(status) = 'pending'
""")
conn.commit()
print(f"\nUpdated {cursor.rowcount} users to 'active' status")

# Verify
print("\nUpdated user statuses:")
cursor.execute("SELECT id, username, status FROM users")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} -> status: '{row[2]}'")

conn.close()
print("\nDone!")
