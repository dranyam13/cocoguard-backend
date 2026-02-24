import sqlite3

DB_PATH = "cocoguard.db"

# Get the first user id from the users table
GET_USER_SQL = "SELECT id FROM users ORDER BY id ASC LIMIT 1;"
# Update all feedbacks with null user_id to use this user id
UPDATE_FEEDBACK_SQL = "UPDATE feedback SET user_id = ? WHERE user_id IS NULL;"

def update_feedback_user_ids():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(GET_USER_SQL)
        row = cur.fetchone()
        if not row:
            print("No users found in the database.")
            return
        user_id = row[0]
        cur.execute(UPDATE_FEEDBACK_SQL, (user_id,))
        conn.commit()
        print(f"Updated feedbacks with user_id={user_id}.")
    finally:
        conn.close()

if __name__ == "__main__":
    update_feedback_user_ids()
