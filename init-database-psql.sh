#!/bin/bash

# Database Schema Initialization Script (Using psql)
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

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "❌ psql is not installed. Please install PostgreSQL client tools."
    echo "   On macOS: brew install postgresql"
    echo "   On Ubuntu: sudo apt-get install postgresql-client"
    exit 1
fi

echo "✅ psql is available"

# Create database initialization SQL
echo "📝 Creating database initialization SQL..."
cat > init_db.sql << 'EOF'
-- Create database if it doesn't exist
CREATE DATABASE flask_app;

-- Connect to the database
\c flask_app;

-- Create users table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO "user" (name, email) 
VALUES 
    ('John Doe', 'john@example.com'),
    ('Jane Smith', 'jane@example.com'),
    ('Bob Johnson', 'bob@example.com')
ON CONFLICT (email) DO NOTHING;

-- Show tables
\dt

-- Show sample data
SELECT * FROM "user";
EOF

echo "Running database initialization..."
if PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_ENDPOINT}" -U postgres -d postgres -f init_db.sql; then
    echo "✅ Database schema initialized successfully"
else
    echo "❌ Database schema initialization failed"
    exit 1
fi

# Clean up
rm -f init_db.sql

echo ""
echo "🎉 Database initialization completed!"
echo ""
echo "💡 The application should now work correctly."
echo "🌐 Try visiting: http://flask-sre-challenge-alb-1939348128.us-east-1.elb.amazonaws.com"
