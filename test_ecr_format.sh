#!/bin/bash

# Test script to validate ECR repository URL format
echo "Testing ECR repository URL format..."

# Simulate AWS account ID
AWS_ACCOUNT_ID="123456789012"
AWS_REGION="us-east-1"
APP_NAME="flask-sre-challenge"

# Build ECR repository URL
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP_NAME}"

echo "AWS Account ID: ${AWS_ACCOUNT_ID}"
echo "AWS Region: ${AWS_REGION}"
echo "App Name: ${APP_NAME}"
echo "ECR Repository URL: ${ECR_REPO}"

# Test Docker tag format
echo "Docker tag format: ${ECR_REPO}:latest"

# Validate the format
if [[ $ECR_REPO =~ ^[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/[a-zA-Z0-9_-]+$ ]]; then
    echo "✅ ECR repository URL format is valid"
else
    echo "❌ ECR repository URL format is invalid"
    exit 1
fi

echo "✅ All tests passed!"
