#!/bin/bash

# Force ECS Service Update
# This script forces the ECS service to pull the latest Docker image

set -e

echo "🔄 Force ECS Service Update"
echo "=========================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

echo "📋 Configuration:"
echo "• AWS Region: ${AWS_REGION}"
echo "• Application Name: ${APP_NAME}"
echo ""

# Force ECS service update
echo "🔄 Forcing ECS service update..."
aws ecs update-service \
    --cluster ${APP_NAME}-cluster \
    --service ${APP_NAME}-service \
    --force-new-deployment \
    --region ${AWS_REGION}

echo "✅ ECS service update initiated"

# Wait for service to be stable
echo "⏳ Waiting for ECS service to be stable..."
aws ecs wait services-stable \
    --cluster ${APP_NAME}-cluster \
    --services ${APP_NAME}-service \
    --region ${AWS_REGION}

echo "✅ ECS service is now stable"

# Check service status
echo "🔍 Checking service status..."
SERVICE_STATUS=$(aws ecs describe-services \
    --cluster ${APP_NAME}-cluster \
    --services ${APP_NAME}-service \
    --region ${AWS_REGION} \
    --query 'services[0].status' \
    --output text)

RUNNING_TASKS=$(aws ecs describe-services \
    --cluster ${APP_NAME}-cluster \
    --services ${APP_NAME}-service \
    --region ${AWS_REGION} \
    --query 'services[0].runningCount' \
    --output text)

echo "• Service Status: ${SERVICE_STATUS}"
echo "• Running Tasks: ${RUNNING_TASKS}"

if [ "$SERVICE_STATUS" = "ACTIVE" ] && [ "$RUNNING_TASKS" -gt 0 ]; then
    echo "✅ Service is active with running tasks"
else
    echo "❌ Service is not active or no tasks are running"
fi

echo ""
echo "🎉 ECS service update completed!"
echo "🌐 Application URL: http://flask-sre-challenge-alb-1939348128.us-east-1.elb.amazonaws.com"
