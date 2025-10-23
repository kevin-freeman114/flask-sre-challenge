#!/bin/bash

# Comprehensive ALB Cleanup Script
# Handles all ALB dependencies in the correct order

set -e

echo "Comprehensive ALB Cleanup"
echo "============================"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
APP_NAME="flask-sre-challenge"

echo "🔍 Finding ALB resources..."

# Get load balancer ARN
LB_ARN=$(aws elbv2 describe-load-balancers \
    --names "${APP_NAME}-alb" \
    --region ${AWS_REGION} \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$LB_ARN" ] || [ "$LB_ARN" = "None" ]; then
    echo "ℹ️  Load balancer not found"
    exit 0
fi

echo "📋 Load Balancer ARN: ${LB_ARN}"

# Step 1: Delete all listeners and rules
echo "🗑️  Step 1: Deleting listeners and rules..."
LISTENERS=$(aws elbv2 describe-listeners \
    --load-balancer-arn ${LB_ARN} \
    --region ${AWS_REGION} \
    --query 'Listeners[].ListenerArn' \
    --output text 2>/dev/null || echo "")

if [ -n "$LISTENERS" ] && [ "$LISTENERS" != "None" ]; then
    for listener in $LISTENERS; do
        echo "🔍 Processing listener: ${listener}"
        
        # Delete all rules for this listener (except default)
        RULES=$(aws elbv2 describe-rules \
            --listener-arn ${listener} \
            --region ${AWS_REGION} \
            --query 'Rules[?Priority!=`default`].RuleArn' \
            --output text 2>/dev/null || echo "")
        
        if [ -n "$RULES" ] && [ "$RULES" != "None" ]; then
            for rule in $RULES; do
                echo "🗑️  Deleting rule: ${rule}"
                aws elbv2 delete-rule \
                    --rule-arn ${rule} \
                    --region ${AWS_REGION} || echo "⚠️  Failed to delete rule ${rule}"
            done
        fi
        
        # Delete the listener
        echo "🗑️  Deleting listener: ${listener}"
        aws elbv2 delete-listener \
            --listener-arn ${listener} \
            --region ${AWS_REGION} || echo "⚠️  Failed to delete listener ${listener}"
    done
fi

# Step 2: Delete target groups
echo "🗑️  Step 2: Deleting target groups..."
TARGET_GROUPS=$(aws elbv2 describe-target-groups \
    --region ${AWS_REGION} \
    --query "TargetGroups[?contains(TargetGroupName, '${APP_NAME}')].TargetGroupArn" \
    --output text 2>/dev/null || echo "")

if [ -n "$TARGET_GROUPS" ] && [ "$TARGET_GROUPS" != "None" ]; then
    for tg in $TARGET_GROUPS; do
        echo "🗑️  Deleting target group: ${tg}"
        aws elbv2 delete-target-group \
            --target-group-arn ${tg} \
            --region ${AWS_REGION} || echo "⚠️  Failed to delete target group ${tg}"
    done
fi

# Step 3: Delete load balancer
echo "🗑️  Step 3: Deleting load balancer..."
aws elbv2 delete-load-balancer \
    --load-balancer-arn ${LB_ARN} \
    --region ${AWS_REGION} || echo "⚠️  Failed to delete load balancer ${LB_ARN}"

# Wait for resources to be deleted
echo "⏳ Waiting for resources to be deleted..."
sleep 15

echo ""
echo "✅ ALB cleanup completed!"
echo ""
echo "You can now run 'terraform destroy' again."
