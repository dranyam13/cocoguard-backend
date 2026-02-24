"""
Add user_settings table to the database
Run this script to create the user_settings table
"""

from app.database import engine, Base
from app.models import UserSettings
from sqlalchemy import inspect

def add_user_settings_table():
    """Create user_settings table if it doesn't exist"""
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("📋 Existing tables:", existing_tables)
    
    if 'user_settings' in existing_tables:
        print("⚠️  Table 'user_settings' already exists")
        return
    
    print("🔨 Creating user_settings table...")
    
    try:
        # Create only the UserSettings table
        UserSettings.__table__.create(engine, checkfirst=True)
        print("✅ Successfully created user_settings table")
        
        # Verify it was created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'user_settings' in tables:
            print("✓ Verified: user_settings table exists")
            
            # Show columns
            columns = inspector.get_columns('user_settings')
            print("\n📊 Table columns:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        else:
            print("❌ Error: Table was not created")
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        raise

if __name__ == "__main__":
    print("=" * 50)
    print("  Add User Settings Table")
    print("=" * 50)
    print()
    
    add_user_settings_table()
    
    print()
    print("=" * 50)
    print("  Done!")
    print("=" * 50)
