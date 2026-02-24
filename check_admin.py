import sqlite3

conn = sqlite3.connect('c:/xampp/htdocs/cocoguard-backend/cocoguard.db')
cur = conn.cursor()

# Get admin users
cur.execute("SELECT id, username, email, role FROM users WHERE role = 'admin'")
admins = cur.fetchall()
print("Admin users:", admins)

# Get all users
cur.execute("SELECT id, username, email, role FROM users LIMIT 5")
users = cur.fetchall()
print("First 5 users:", users)

conn.close()
