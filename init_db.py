import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, engine, Base
from app.models import User, UserRole, UserStatus
from app.auth_utils import get_password_hash

# Create all tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✓ Tables created")

# Create a new session
db = SessionLocal()

try:
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == "Admin").first()
    if existing_user:
        print(f"✓ User already exists (ID: {existing_user.id})")
        db.close()
        sys.exit(0)
    
    # Create new admin user with argon2 hash
    print("Creating admin user...")
    hashed_password = get_password_hash("Admin")
    
    new_user = User(
        username="Admin",
        email="Admin",
        password_hash=hashed_password,
        role=UserRole.admin,
        status=UserStatus.active,
        full_name="Administrator"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"✓ Admin user created successfully!")
    print(f"\n📝 Login Credentials:")
    print(f"   Email: Admin")
    print(f"   Password: Admin")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    db.rollback()
    sys.exit(1)
finally:
    db.close()
