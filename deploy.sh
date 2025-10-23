#!/bin/bash

# Deployment script for Flask SRE Challenge
set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

echo "Starting deployment process..."

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

# Authenticate with AWS and get account ID
echo "🔐 Authenticating with AWS..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Failed to get AWS account ID. Please check your AWS credentials."
    exit 1
fi

echo "✅ AWS Account ID: ${AWS_ACCOUNT_ID}"

# Set ECR repository URL
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP_NAME}"
echo "📦 ECR Repository: ${ECR_REPO}"

# Check if ECR repository exists, create if it doesn't
echo "🔍 Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names ${APP_NAME} --region ${AWS_REGION} &> /dev/null; then
    echo "📦 Creating ECR repository..."
    aws ecr create-repository \
        --repository-name ${APP_NAME} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true
    echo "✅ ECR repository created successfully"
else
    echo "✅ ECR repository already exists"
fi

# Import existing ECR repository into Terraform state if needed
echo "🔄 Importing ECR repository into Terraform state..."
cd terraform
if ! terraform state show aws_ecr_repository.app &> /dev/null; then
    echo "📥 Importing existing ECR repository into Terraform state..."
    terraform import aws_ecr_repository.app ${APP_NAME} || echo "⚠️  ECR repository import failed, continuing..."
fi
cd ..

# Build and push Docker image for linux/amd64 platform (required for ECS Fargate)
echo "🐳 Building Docker image for linux/amd64 platform..."
docker build --platform linux/amd64 -t ${APP_NAME}:latest .

# Tag image for ECR
echo "🏷️ Tagging image for ECR..."
docker tag ${APP_NAME}:latest ${ECR_REPO}:latest

# Login to ECR
echo "🔑 Logging into ECR..."
if ! aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com; then
    echo "❌ Failed to login to ECR. Please check your AWS credentials and permissions."
    exit 1
fi

# Push image to ECR
echo "📤 Pushing image to ECR..."
if ! docker push ${ECR_REPO}:latest; then
    echo "❌ Failed to push image to ECR. Please check your permissions and network connection."
    exit 1
fi

echo "✅ Successfully pushed image to ECR: ${ECR_REPO}:latest"

# Deploy infrastructure with Terraform
echo "Deploying infrastructure with Terraform..."
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
