#!/bin/bash

# Daily Uplift SMS Deployment Script

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check for SAM CLI
if ! command -v sam &> /dev/null; then
    echo "AWS SAM CLI is not installed. Please install it first."
    exit 1
fi

# Set variables
STACK_NAME="daily-uplift-sms"
TEMPLATE_FILE="template.yaml"
REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
    REGION="us-east-1"  # Default region
fi

# Build and deploy
echo "Building and deploying Daily Uplift SMS to region $REGION..."

# Package static files
echo "Packaging static files..."
mkdir -p ../build
cp -r ../src/* ../build/

# Deploy with SAM
echo "Deploying with SAM..."
sam build -t $TEMPLATE_FILE
sam deploy --stack-name $STACK_NAME --capabilities CAPABILITY_IAM --no-confirm-changeset

# Get outputs
echo "Deployment complete. Getting outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text)
API_KEY=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ApiKey'].OutputValue" --output text)
SNS_TOPIC_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='UpliftSMSTopicARN'].OutputValue" --output text)

echo ""
echo "====== Deployment Information ======"
echo "API Endpoint: $API_ENDPOINT"
echo "API Key: $API_KEY"
echo "SNS Topic ARN: $SNS_TOPIC_ARN"
echo ""
echo "To add a subscriber, run:"
echo "python ../src/manage_subscriber.py --action subscribe --topic-arn \"$SNS_TOPIC_ARN\" --phone \"+1234567890\" --category motivation"
echo ""
echo "To update the dashboard.js with your API endpoint and key:"
echo "1. Edit ../src/static/js/dashboard.js"
echo "2. Update API_URL to: $API_ENDPOINT"
echo "3. Update API_KEY to: $API_KEY"
echo ""
echo "Redeploy the stack after making these changes."
echo "==============================="