#!/bin/bash

# Fix ALB Target Group Cleanup Issue
# This script handles the case where target groups cannot be deleted due to dependencies

set -e

echo "ALB Target Group Cleanup Fix"
echo "==============================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"
TARGET_GROUP_NAME="${APP_NAME}-tg"

echo "🔍 Checking ALB and target group status..."

# Get the target group ARN
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names ${TARGET_GROUP_NAME} \
    --region ${AWS_REGION} \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$TARGET_GROUP_ARN" ] || [ "$TARGET_GROUP_ARN" = "None" ]; then
    echo "ℹ️  Target group not found or already deleted"
    exit 0
fi

echo "📋 Target Group ARN: ${TARGET_GROUP_ARN}"

# Get the load balancer ARN
LB_ARN=$(aws elbv2 describe-target-groups \
    --target-group-arns ${TARGET_GROUP_ARN} \
    --region ${AWS_REGION} \
    --query 'TargetGroups[0].LoadBalancerArns[0]' \
    --output text 2>/dev/null || echo "")

if [ -n "$LB_ARN" ] && [ "$LB_ARN" != "None" ]; then
    echo "📋 Load Balancer ARN: ${LB_ARN}"
    
    # Get listeners
    echo "🔍 Checking listeners..."
    LISTENERS=$(aws elbv2 describe-listeners \
        --load-balancer-arn ${LB_ARN} \
        --region ${AWS_REGION} \
        --query 'Listeners[].ListenerArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$LISTENERS" ] && [ "$LISTENERS" != "None" ]; then
        echo "📋 Found listeners: ${LISTENERS}"
        
        # Delete listeners first
        for listener in $LISTENERS; do
            echo "🗑️  Deleting listener: ${listener}"
            aws elbv2 delete-listener \
                --listener-arn ${listener} \
                --region ${AWS_REGION} || echo "⚠️  Failed to delete listener ${listener}"
        done
    fi
    
    # Get rules for each listener
    for listener in $LISTENERS; do
        if [ -n "$listener" ] && [ "$listener" != "None" ]; then
            echo "🔍 Checking rules for listener: ${listener}"
            RULES=$(aws elbv2 describe-rules \
                --listener-arn ${listener} \
                --region ${AWS_REGION} \
                --query 'Rules[?Priority!=`default`].RuleArn' \
                --output text 2>/dev/null || echo "")
            
            if [ -n "$RULES" ] && [ "$RULES" != "None" ]; then
                echo "📋 Found rules: ${RULES}"
                for rule in $RULES; do
                    echo "🗑️  Deleting rule: ${rule}"
                    aws elbv2 delete-rule \
                        --rule-arn ${rule} \
                        --region ${AWS_REGION} || echo "⚠️  Failed to delete rule ${rule}"
                done
            fi
        fi
    done
fi

# Wait a bit for dependencies to clear
echo "⏳ Waiting for dependencies to clear..."
sleep 10

# Try to delete the target group
echo "🗑️  Attempting to delete target group..."
aws elbv2 delete-target-group \
    --target-group-arn ${TARGET_GROUP_ARN} \
    --region ${AWS_REGION} || echo "⚠️  Target group still in use, may need manual cleanup"

echo ""
echo "✅ ALB cleanup attempt completed!"
echo ""
echo "If the target group is still in use, you may need to:"
echo "1. Check for any remaining listeners or rules"
echo "2. Manually delete the load balancer first"
echo "3. Then delete the target group"
