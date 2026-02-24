#!/usr/bin/env python
"""Reset all admin users and create a fresh one with provided credentials."""

import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, engine, Base
from app.models import User, UserRole, UserStatus
from app.auth_utils import get_password_hash

# Ensure tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

NEW_EMAIL = "cocoguard@admin.com"
NEW_USERNAME = "admin"
NEW_PASSWORD = "cocoadmin"

try:
    # Remove existing admin users
    admins = db.query(User).filter(User.role == UserRole.admin).all()
    removed = 0
    for admin in admins:
        db.delete(admin)
        removed += 1
    if removed:
        print(f"Removed {removed} existing admin user(s)")

    # Create new admin user
    hashed_password = get_password_hash(NEW_PASSWORD)
    new_user = User(
        username=NEW_USERNAME,
        email=NEW_EMAIL,
        password_hash=hashed_password,
        role=UserRole.admin,
        status=UserStatus.active,
        full_name="Admin User",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    print("✓ Admin user created successfully!")
    print(f"  ID: {new_user.id}")
    print(f"  Email: {new_user.email}")
    print(f"  Username: {new_user.username}")
    print(f"\nYou can now login with:")
    print(f"  Email/Username: {NEW_EMAIL}")
    print(f"  Password: {NEW_PASSWORD}")

except Exception as e:
    db.rollback()
    print(f"✗ Error resetting admin user: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()
