#!/bin/bash

# Quick fix for ECR repository cleanup
# Use this when Terraform destroy fails due to ECR repository not being empty

set -e

echo "ECR Quick Fix Script"
echo "======================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

echo "🗑️  Manually cleaning up ECR repository..."

# Delete all images first
echo "📦 Deleting all images in ECR repository..."
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
echo "🎉 ECR cleanup completed!"
echo ""
echo "You can now run 'terraform destroy' again to complete the cleanup."
