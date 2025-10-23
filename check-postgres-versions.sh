#!/bin/bash

# Check available PostgreSQL versions in AWS RDS
# This script helps identify supported PostgreSQL versions

set -e

echo "🔍 Available PostgreSQL Versions in AWS RDS"
echo "==========================================="

AWS_REGION=${AWS_REGION:-us-east-1}

echo "Checking PostgreSQL versions in region: ${AWS_REGION}"
echo ""

# Get all PostgreSQL versions
echo "📋 All PostgreSQL versions:"
aws rds describe-db-engine-versions \
    --engine postgres \
    --region ${AWS_REGION} \
    --query 'DBEngineVersions[].EngineVersion' \
    --output table

echo ""
echo "📋 Latest versions by major version:"

# Get latest versions for each major version
for major in 11 12 13 14 15; do
    echo "PostgreSQL ${major}.x:"
    aws rds describe-db-engine-versions \
        --engine postgres \
        --region ${AWS_REGION} \
        --query "DBEngineVersions[?starts_with(EngineVersion, '${major}.')].EngineVersion" \
        --output table | head -5
    echo ""
done

echo "✅ Use one of the versions above in your Terraform configuration"

