import sys
sys.path.insert(0, '.')

from app.database import SessionLocal

db = SessionLocal()

try:
    # Update the admin user's email
    from app.models import User
    admin_user = db.query(User).filter(User.username == "Admin").first()
    
    if admin_user:
        admin_user.email = "admin@cocoguard.com"
        db.commit()
        print(f"✓ Email updated successfully!")
        print(f"  Username: {admin_user.username}")
        print(f"  New Email: {admin_user.email}")
    else:
        print("✗ Admin user not found")
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
