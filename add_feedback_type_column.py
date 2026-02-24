import sqlite3

DB_PATH = "cocoguard.db"

ALTER_SQL = "ALTER TABLE feedback ADD COLUMN type VARCHAR(50);"

def add_type_column():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(ALTER_SQL)
        print("Successfully added 'type' column to feedback table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'type' already exists.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_type_column()
