#!/bin/bash

# Cleanup script for Flask SRE Challenge
# Use this if you need to clean up existing resources

set -e

echo "🧹 Flask SRE Challenge Cleanup Script"
echo "====================================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: ${AWS_ACCOUNT_ID}"

echo ""
echo "⚠️  WARNING: This will destroy all resources created by Terraform!"
echo "This includes:"
echo "- VPC and networking resources"
echo "- ECS cluster and service"
echo "- RDS database (data will be lost!)"
echo "- Application Load Balancer"
echo "- ECR repository"
echo ""

read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cleanup cancelled"
    exit 0
fi

echo ""
echo "🗑️  Destroying Terraform resources..."

cd terraform

# Try to destroy Terraform resources
echo "🔄 Attempting Terraform destroy..."
if ! terraform destroy -auto-approve; then
    echo "⚠️  Terraform destroy failed, trying to fix ALB dependencies..."
    cd ..
    ./cleanup-alb.sh
    echo ""
    echo "🔄 Retrying Terraform destroy..."
    cd terraform
    terraform destroy -auto-approve
fi

echo ""
echo "✅ Terraform resources destroyed"

# Optional: Delete ECR repository
echo ""
read -p "Do you want to delete the ECR repository? (yes/no): " delete_ecr

if [ "$delete_ecr" = "yes" ]; then
    echo "🗑️  Running ECR cleanup script..."
    ./cleanup-ecr.sh
fi

echo ""
echo "🎉 Cleanup completed successfully!"
echo ""
echo "All resources have been destroyed."
echo "You can now run the deployment script again if needed."
