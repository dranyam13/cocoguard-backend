import sqlite3

DB_PATH = r'C:/xampp/htdocs/cocoguard-backend/cocoguard.db'  # Absolute path to your SQLite database

def add_status_column():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE feedback ADD COLUMN status TEXT DEFAULT 'Received'")
        print("Added 'status' column to feedback table.")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("Column 'status' already exists.")
        else:
            print(f"Error: {e}")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    add_status_column()
