#!/usr/bin/env python
"""Script to create an admin user in the database"""

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
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == "admin@cocoguard.com").first()
    if existing_user:
        print(f"User with email 'admin@cocoguard.com' already exists (ID: {existing_user.id})")
        print("Updating password hash to ensure it's correct...")
        existing_user.password_hash = get_password_hash("cocoguard")
        existing_user.status = UserStatus.active
        existing_user.role = UserRole.admin
        db.commit()
        print("✓ Password updated successfully!")
        print(f"\nYou can now login with:")
        print(f"  Email/Username: admin@cocoguard.com")
        print(f"  Password: cocoguard")
        db.close()
        sys.exit(0)
    
    # Hash password properly using auth_utils
    hashed_password = get_password_hash("cocoguard")
    
    new_user = User(
        username="admin",
        email="admin@cocoguard.com",
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
    print(f"  Email/Username: admin@cocoguard.com")
    print(f"  Password: cocoguard")
    
except Exception as e:
    print(f"✗ Error creating user: {str(e)}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
