#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def init_database():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            print("✅ Database connection successful")
            
            # Create database if it doesn't exist
            db_name = "flask_app"
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
            print(f"✅ Database '{db_name}' created/verified")
            
            # Use the database
            conn.execute(text(f"USE {db_name}"))
            
            # Create users table
            create_users_table = """
            CREATE TABLE IF NOT EXISTS "user" (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            conn.execute(text(create_users_table))
            print("✅ Users table created/verified")
            
            # Insert sample data
            insert_sample_data = """
            INSERT INTO "user" (name, email) 
            VALUES 
                ('John Doe', 'john@example.com'),
                ('Jane Smith', 'jane@example.com'),
                ('Bob Johnson', 'bob@example.com')
            ON CONFLICT (email) DO NOTHING;
            """
            
            conn.execute(text(insert_sample_data))
            print("✅ Sample data inserted")
            
            # Commit changes
            conn.commit()
            print("✅ Database initialization completed successfully")
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
