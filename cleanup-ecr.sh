#!/bin/bash

# ECR Cleanup script for Flask SRE Challenge
# This script specifically handles ECR repository cleanup

set -e

echo "🧹 ECR Cleanup Script"
echo "===================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: ${AWS_ACCOUNT_ID}"

echo ""
echo "🔍 Checking ECR repository: ${APP_NAME}"

# Check if repository exists
if ! aws ecr describe-repositories --repository-names ${APP_NAME} --region ${AWS_REGION} &> /dev/null; then
    echo "ℹ️  ECR repository does not exist"
    exit 0
fi

echo "📦 ECR repository found"

# List all images
echo "🔍 Listing images in repository..."
aws ecr list-images --repository-name ${APP_NAME} --region ${AWS_REGION} --query 'imageIds[*]' --output table

echo ""
read -p "Do you want to delete all images and the repository? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ ECR cleanup cancelled"
    exit 0
fi

# Delete all images
echo "🗑️  Deleting all images..."
aws ecr list-images --repository-name ${APP_NAME} --region ${AWS_REGION} --query 'imageIds[*]' --output json > /tmp/image-ids.json

if [ -s /tmp/image-ids.json ] && [ "$(cat /tmp/image-ids.json)" != "[]" ]; then
    aws ecr batch-delete-image \
        --repository-name ${APP_NAME} \
        --region ${AWS_REGION} \
        --image-ids file:///tmp/image-ids.json
    echo "✅ All images deleted"
else
    echo "ℹ️  No images found"
fi

# Delete the repository
echo "🗑️  Deleting ECR repository..."
aws ecr delete-repository \
    --repository-name ${APP_NAME} \
    --region ${AWS_REGION} \
    --force

echo "✅ ECR repository deleted"

# Clean up temp file
rm -f /tmp/image-ids.json

echo ""
echo "🎉 ECR cleanup completed successfully!"
