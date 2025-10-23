#!/bin/bash

# Database Schema Initialization Script
# This script initializes the database schema for the Flask application

set -e

echo "Database Schema Initialization"
echo "================================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

echo "📋 Configuration:"
echo "• AWS Region: ${AWS_REGION}"
echo "• Application Name: ${APP_NAME}"
echo ""

# Get database endpoint
echo "🔍 Getting database endpoint..."
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier ${APP_NAME}-db \
    --region ${AWS_REGION} \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text 2>/dev/null || echo "")

if [ -z "$DB_ENDPOINT" ] || [ "$DB_ENDPOINT" = "None" ]; then
    echo "❌ Could not get database endpoint"
    exit 1
fi

echo "• Database Endpoint: ${DB_ENDPOINT}"

# Get database password from Terraform
echo "🔍 Getting database password..."
cd terraform
DB_PASSWORD=$(terraform output -raw db_password 2>/dev/null || echo "password")
cd ..

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Could not get database password from Terraform"
    exit 1
fi

echo "• Database Password: [HIDDEN]"

# Create database initialization script
echo "📝 Creating database initialization script..."
cat > init_db.py << 'EOF'
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
EOF

chmod +x init_db.py

# Set environment variables
export DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@${DB_ENDPOINT}:5432/flask_app"

echo "Running database initialization..."
if python3 init_db.py; then
    echo "✅ Database schema initialized successfully"
else
    echo "❌ Database schema initialization failed"
    exit 1
fi

# Clean up
rm -f init_db.py

echo ""
echo "🎉 Database initialization completed!"
echo ""
echo "💡 The application should now work correctly."
echo "🌐 Try visiting: http://flask-sre-challenge-alb-1939348128.us-east-1.elb.amazonaws.com"
