#!/usr/bin/env python
"""Script to create a farmer user account for testing"""

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
    # Check if user already exists by email
    existing_user = db.query(User).filter(User.email == "farmer@cocoguard.com").first()
    if existing_user:
        print(f"User with email 'farmer@cocoguard.com' already exists (ID: {existing_user.id})")
        db.close()
        sys.exit(0)
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == "farmer").first()
    if existing_user:
        print(f"User with username 'farmer' already exists (ID: {existing_user.id})")
        db.close()
        sys.exit(0)
    
    # Hash the password properly
    hashed_password = get_password_hash("cocoguard")
    
    new_user = User(
        username="farmer",
        email="farmer@cocoguard.com",
        password_hash=hashed_password,
        role=UserRole.user,
        status=UserStatus.active,
        full_name="Test Farmer"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"✓ Farmer user created successfully!")
    print(f"  ID: {new_user.id}")
    print(f"  Email: {new_user.email}")
    print(f"  Username: {new_user.username}")
    print(f"  Role: {new_user.role}")
    print(f"\nYou can now login with:")
    print(f"  Email/Username: farmer@cocoguard.com")
    print(f"  Password: cocoguard")
    
except Exception as e:
    print(f"✗ Error creating user: {str(e)}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
