#!/usr/bin/env python3
"""
Database schema fix script
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_database():
    """Fix database schema issues"""
    try:
        # Get database URL
        database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/flask_app.db')
        
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if created_at column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user' AND column_name = 'created_at'
            """))
            
            if not result.fetchone():
                print("Adding created_at column to user table...")
                conn.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """))
                conn.commit()
                print("✅ created_at column added successfully")
            else:
                print("✅ created_at column already exists")
                
        print("Database schema fix completed successfully")
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        sys.exit(1)

if __name__ == '__main__':
    fix_database()
