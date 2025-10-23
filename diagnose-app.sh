#!/bin/bash

# Application Diagnostic Script
# This script helps diagnose internal server errors and application issues

set -e

echo "🔍 Application Diagnostic Script"
echo "================================"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"
ALB_DNS="flask-sre-challenge-alb-1939348128.us-east-1.elb.amazonaws.com"

echo "📋 Configuration:"
echo "• AWS Region: ${AWS_REGION}"
echo "• Application Name: ${APP_NAME}"
echo "• ALB DNS: ${ALB_DNS}"
echo ""

# 1. Check ECS Service Status
echo "🔍 1. Checking ECS Service Status..."
echo "===================================="

SERVICE_STATUS=$(aws ecs describe-services \
    --cluster ${APP_NAME}-cluster \
    --services ${APP_NAME}-service \
    --region ${AWS_REGION} \
    --query 'services[0].status' \
    --output text 2>/dev/null || echo "UNKNOWN")

echo "• ECS Service Status: ${SERVICE_STATUS}"

if [ "$SERVICE_STATUS" = "ACTIVE" ]; then
    echo "✅ ECS Service is active"
else
    echo "❌ ECS Service is not active"
fi

# Check running tasks
RUNNING_TASKS=$(aws ecs describe-services \
    --cluster ${APP_NAME}-cluster \
    --services ${APP_NAME}-service \
    --region ${AWS_REGION} \
    --query 'services[0].runningCount' \
    --output text 2>/dev/null || echo "0")

echo "• Running Tasks: ${RUNNING_TASKS}"

if [ "$RUNNING_TASKS" -gt 0 ]; then
    echo "✅ Tasks are running"
else
    echo "❌ No tasks are running"
fi

# 2. Check ECS Task Status
echo ""
echo "🔍 2. Checking ECS Task Status..."
echo "================================="

TASK_ARNS=$(aws ecs list-tasks \
    --cluster ${APP_NAME}-cluster \
    --service-name ${APP_NAME}-service \
    --region ${AWS_REGION} \
    --query 'taskArns' \
    --output text 2>/dev/null || echo "")

if [ -n "$TASK_ARNS" ] && [ "$TASK_ARNS" != "None" ]; then
    echo "• Found ${RUNNING_TASKS} task(s)"
    
    for task_arn in $TASK_ARNS; do
        TASK_STATUS=$(aws ecs describe-tasks \
            --cluster ${APP_NAME}-cluster \
            --tasks ${task_arn} \
            --region ${AWS_REGION} \
            --query 'tasks[0].lastStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")
        
        echo "• Task ${task_arn}: ${TASK_STATUS}"
        
        if [ "$TASK_STATUS" = "RUNNING" ]; then
            echo "✅ Task is running"
        else
            echo "❌ Task is not running"
        fi
    done
else
    echo "❌ No tasks found"
fi

# 3. Check Application Logs
echo ""
echo "🔍 3. Checking Application Logs..."
echo "================================="

LOG_GROUP="/ecs/${APP_NAME}-task"
echo "• Log Group: ${LOG_GROUP}"

# Check if log group exists
if aws logs describe-log-groups --log-group-name-prefix ${LOG_GROUP} --region ${AWS_REGION} --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q ${LOG_GROUP}; then
    echo "✅ Log group exists"
    
    # Get recent log streams
    LOG_STREAMS=$(aws logs describe-log-streams \
        --log-group-name ${LOG_GROUP} \
        --region ${AWS_REGION} \
        --order-by LastEventTime \
        --descending \
        --max-items 5 \
        --query 'logStreams[].logStreamName' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$LOG_STREAMS" ] && [ "$LOG_STREAMS" != "None" ]; then
        echo "• Recent log streams found"
        
        # Get logs from the most recent stream
        LATEST_STREAM=$(echo $LOG_STREAMS | cut -d' ' -f1)
        echo "• Latest stream: ${LATEST_STREAM}"
        
        echo ""
        echo "📋 Recent Application Logs:"
        echo "--------------------------"
        aws logs get-log-events \
            --log-group-name ${LOG_GROUP} \
            --log-stream-name ${LATEST_STREAM} \
            --region ${AWS_REGION} \
            --start-time $(date -d '1 hour ago' +%s)000 \
            --query 'events[].message' \
            --output text 2>/dev/null | tail -20 || echo "No recent logs found"
    else
        echo "❌ No log streams found"
    fi
else
    echo "❌ Log group does not exist"
fi

# 4. Check Database Status
echo ""
echo "🔍 4. Checking Database Status..."
echo "================================"

DB_STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier ${APP_NAME}-db \
    --region ${AWS_REGION} \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text 2>/dev/null || echo "UNKNOWN")

echo "• Database Status: ${DB_STATUS}"

if [ "$DB_STATUS" = "available" ]; then
    echo "✅ Database is available"
else
    echo "❌ Database is not available"
fi

# 5. Check ALB Target Group Health
echo ""
echo "🔍 5. Checking ALB Target Group Health..."
echo "========================================="

TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names ${APP_NAME}-tg \
    --region ${AWS_REGION} \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || echo "")

if [ -n "$TARGET_GROUP_ARN" ] && [ "$TARGET_GROUP_ARN" != "None" ]; then
    echo "• Target Group ARN: ${TARGET_GROUP_ARN}"
    
    # Check target health
    TARGET_HEALTH=$(aws elbv2 describe-target-health \
        --target-group-arn ${TARGET_GROUP_ARN} \
        --region ${AWS_REGION} \
        --query 'TargetHealthDescriptions[].TargetHealth' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$TARGET_HEALTH" ] && [ "$TARGET_HEALTH" != "None" ]; then
        echo "• Target Health: ${TARGET_HEALTH}"
        
        if echo "$TARGET_HEALTH" | grep -q "healthy"; then
            echo "✅ Targets are healthy"
        else
            echo "❌ Targets are not healthy"
        fi
    else
        echo "❌ No targets found"
    fi
else
    echo "❌ Target group not found"
fi

# 6. Test Health Endpoints
echo ""
echo "🔍 6. Testing Health Endpoints..."
echo "================================="

echo "• Testing ALB endpoint: http://${ALB_DNS}"
echo "• Testing health endpoint: http://${ALB_DNS}/health"

# Test basic connectivity
if curl -s --max-time 10 http://${ALB_DNS} >/dev/null 2>&1; then
    echo "✅ ALB endpoint is reachable"
else
    echo "❌ ALB endpoint is not reachable"
fi

# Test health endpoint
if curl -s --max-time 10 http://${ALB_DNS}/health >/dev/null 2>&1; then
    echo "✅ Health endpoint is reachable"
else
    echo "❌ Health endpoint is not reachable"
fi

echo ""
echo "Diagnostic Summary:"
echo "====================="
echo "• ECS Service: ${SERVICE_STATUS}"
echo "• Running Tasks: ${RUNNING_TASKS}"
echo "• Database: ${DB_STATUS}"
echo "• ALB Endpoint: http://${ALB_DNS}"
echo ""
echo "💡 Next Steps:"
echo "• Check the logs above for specific error messages"
echo "• Verify database connectivity if tasks are running"
echo "• Check ECS task definition and environment variables"
echo "• Ensure all required environment variables are set"
