#!/bin/bash

# Fix Docker Platform Issue for ECS Fargate
# This script rebuilds the Docker image for linux/amd64 platform

set -e

echo "Docker Platform Fix for ECS Fargate"
echo "======================================"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: ${AWS_ACCOUNT_ID}"

# ECR Repository URL
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP_NAME}"

echo "📋 ECR Repository: ${ECR_REPO}"

# Check if ECR repository exists
echo "🔍 Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names ${APP_NAME} --region ${AWS_REGION} >/dev/null 2>&1; then
    echo "❌ ECR repository not found. Please run the deployment script first."
    exit 1
fi

echo "✅ ECR repository found"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

# Build image for linux/amd64 platform
echo "🐳 Building Docker image for linux/amd64 platform..."
docker build --platform linux/amd64 -t ${APP_NAME}:latest .

# Tag image for ECR
echo "🏷️  Tagging image for ECR..."
docker tag ${APP_NAME}:latest ${ECR_REPO}:latest

# Push image to ECR
echo "📤 Pushing image to ECR..."
docker push ${ECR_REPO}:latest

echo ""
echo "✅ Docker image rebuilt and pushed for linux/amd64 platform"
echo ""
echo "🔄 The ECS service should now be able to pull the image successfully."
echo "You can check the ECS service status in the AWS console."
