import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.auth_utils import get_password_hash

db = SessionLocal()

try:
    # Update the admin user's password
    from app.models import User
    admin_user = db.query(User).filter(User.username == "Admin").first()
    
    if admin_user:
        hashed_password = get_password_hash("cocoguard")
        admin_user.password_hash = hashed_password
        db.commit()
        print(f"✓ Password updated successfully!")
        print(f"  Username: {admin_user.username}")
        print(f"  Email: {admin_user.email}")
        print(f"\n📝 New Login Credentials:")
        print(f"   Email: admin@cocoguard.com")
        print(f"   Password: cocoguard")
    else:
        print("✗ Admin user not found")
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
