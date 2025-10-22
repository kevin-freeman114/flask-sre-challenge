#!/bin/bash

# Deployment script for Flask SRE Challenge
set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP_NAME}"

echo "🚀 Starting deployment process..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install it first."
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform is not installed. Please install it first."
    exit 1
fi

# Authenticate with AWS
echo "🔐 Authenticating with AWS..."
aws sts get-caller-identity

# Build and push Docker image
echo "🐳 Building Docker image..."
docker build -t ${APP_NAME}:latest .

# Tag image for ECR
docker tag ${APP_NAME}:latest ${ECR_REPO}:latest

# Login to ECR
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

# Push image to ECR
echo "📤 Pushing image to ECR..."
docker push ${ECR_REPO}:latest

# Deploy infrastructure with Terraform
echo "🏗️ Deploying infrastructure with Terraform..."
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="aws_region=${AWS_REGION}" -out=tfplan

# Apply deployment
terraform apply tfplan

# Get outputs
ALB_DNS=$(terraform output -raw alb_dns_name)
ECR_URL=$(terraform output -raw ecr_repository_url)

echo "✅ Deployment completed successfully!"
echo "🌐 Application URL: http://${ALB_DNS}"
echo "📦 ECR Repository: ${ECR_URL}"

# Wait for ECS service to be stable
echo "⏳ Waiting for ECS service to be stable..."
aws ecs wait services-stable \
    --cluster ${APP_NAME}-cluster \
    --services ${APP_NAME}-service \
    --region ${AWS_REGION}

echo "🎉 Application is now running at: http://${ALB_DNS}"
echo "🔍 Health check: http://${ALB_DNS}/health"
