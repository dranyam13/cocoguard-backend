import sqlite3

conn = sqlite3.connect('cocoguard.db')
cursor = conn.cursor()
cursor.execute('SELECT id, email, username, password_hash FROM users LIMIT 5')
rows = cursor.fetchall()
print('Current users in database:')
for row in rows:
    print(f'  ID: {row[0]}, Email: {row[1]}, Username: {row[2]}')
    print(f'    Hash: {row[3][:50]}...')
conn.close()
