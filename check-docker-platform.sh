#!/bin/bash

# Docker Platform Check and Fix Script
# This script checks Docker platform compatibility and provides fixes

set -e

echo "🔍 Docker Platform Compatibility Check"
echo "======================================"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP_NAME}"

echo "📋 Current Configuration:"
echo "• AWS Region: ${AWS_REGION}"
echo "• ECR Repository: ${ECR_REPO}"
echo "• Required Platform: linux/amd64 (for ECS Fargate)"
echo ""

# Check current Docker platform
echo "🔍 Checking Docker platform..."
CURRENT_PLATFORM=$(docker version --format '{{.Server.Arch}}')
echo "• Current Docker Platform: ${CURRENT_PLATFORM}"

# Check if we're on Apple Silicon
if [[ "$(uname -m)" == "arm64" ]]; then
    echo "• Detected: Apple Silicon Mac (ARM64)"
    echo "• Issue: Docker images built on ARM64 won't work on ECS Fargate (linux/amd64)"
    echo "• Solution: Use --platform linux/amd64 when building"
else
    echo "• Detected: x86_64 system"
    echo "• Status: Should work fine with ECS Fargate"
fi

echo ""
echo "Available Fixes:"

echo ""
echo "1. Quick Fix (Rebuild for correct platform):"
echo "   ./fix-docker-platform.sh"
echo ""

echo "2. Manual Fix:"
echo "   docker build --platform linux/amd64 -t ${APP_NAME}:latest ."
echo "   docker tag ${APP_NAME}:latest ${ECR_REPO}:latest"
echo "   aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}"
echo "   docker push ${ECR_REPO}:latest"
echo ""

echo "3. Check ECS Service Status:"
echo "   aws ecs describe-services --cluster ${APP_NAME}-cluster --services ${APP_NAME}-service --region ${AWS_REGION}"
echo ""

echo "4. Check ECS Task Logs:"
echo "   aws logs describe-log-groups --log-group-name-prefix /ecs/${APP_NAME} --region ${AWS_REGION}"
echo ""

echo "📋 Platform Compatibility Matrix:"
echo "• Apple Silicon (ARM64) → ECS Fargate (linux/amd64): ❌ Incompatible"
echo "• Apple Silicon (ARM64) → ECS Fargate (linux/amd64) with --platform: ✅ Compatible"
echo "• x86_64 → ECS Fargate (linux/amd64): ✅ Compatible"
echo "• x86_64 → ECS Fargate (linux/amd64) with --platform: ✅ Compatible"
