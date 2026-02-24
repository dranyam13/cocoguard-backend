import sqlite3

# Delete the old user
conn = sqlite3.connect('cocoguard.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM users WHERE id = 1')
conn.commit()
print('Old user deleted')
conn.close()

# Now create a new user with argon2 hash
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, engine, Base
from app.models import User, UserRole, UserStatus
from app.auth_utils import get_password_hash

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create a new session
db = SessionLocal()

try:
    # Create new admin user
    hashed_password = get_password_hash("Admin")
    print(f"Hashed password: {hashed_password}")
    
    new_user = User(
        username="Admin",
        email="Admin",
        password_hash=hashed_password,
        role=UserRole.admin,
        status=UserStatus.active,
        full_name="Admin User"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"✓ Admin user created successfully!")
    print(f"  ID: {new_user.id}")
    print(f"  Email: {new_user.email}")
    print(f"  Username: {new_user.username}")
    print(f"  Role: {new_user.role}")
    print(f"\nYou can now login with:")
    print(f"  Email/Username: Admin")
    print(f"  Password: Admin")
    
except Exception as e:
    print(f"✗ Error creating user: {str(e)}")
    import traceback
    traceback.print_exc()
    db.rollback()
    sys.exit(1)
finally:
    db.close()
