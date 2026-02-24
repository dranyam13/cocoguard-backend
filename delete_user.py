from app.database import SessionLocal
from app.models import User

db = SessionLocal()

try:
    user = db.query(User).filter(User.username == 'farmermaynard').first()
    
    if user:
        print(f'Found user: {user.username} (ID: {user.id}, Email: {user.email})')
        db.delete(user)
        db.commit()
        print('User deleted successfully!')
    else:
        print('User "farmermaynard" not found in database.')
        
except Exception as e:
    print(f'Error: {e}')
    db.rollback()
finally:
    db.close()
