# Testing Daily Uplift SMS on AWS

This guide provides step-by-step instructions for testing the Daily Uplift SMS project on AWS.

## 1. Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured with your credentials
- AWS SAM CLI installed

## 2. Deployment

```bash
# Navigate to deployment directory
cd /workspaces/daily-uplift-sms/deployment

# Run the deployment script
./deploy.sh
```

The script will output important information including:
- API Endpoint URL
- API Key
- SNS Topic ARN

## 3. Testing the Lambda Function

### Test scheduled message delivery:

```bash
# Manually invoke the Lambda function
aws lambda invoke --function-name daily-uplift-sms-UpliftLambdaFunction \
  --payload '{}' response.json

# Check the response
cat response.json
```

## 4. Testing Subscriber Management

### Add a subscriber:

```bash
cd /workspaces/daily-uplift-sms/src
python manage_subscriber.py --action subscribe --topic-arn "YOUR_SNS_TOPIC_ARN" --phone "+1234567890" --category motivation
```

### Update subscriber preferences:

```bash
python manage_subscriber.py --action update --phone "+1234567890" --category mindfulness
```

### Verify in DynamoDB:

```bash
aws dynamodb scan --table-name daily-uplift-subscribers
```

## 5. Testing the Admin Dashboard

### Update API configuration:

1. Edit `/src/static/js/dashboard.js`
2. Update these variables with values from deployment output:
   ```javascript
   const API_URL = 'https://your-api-id.execute-api.region.amazonaws.com/prod';
   const API_KEY = 'your-api-key';
   ```
3. Redeploy if needed

### Access the dashboard:

Open the API Gateway URL in your browser:
```
https://your-api-id.execute-api.region.amazonaws.com/prod
```

### Test dashboard features:

1. Add/update subscribers
2. Send test messages
3. View analytics

## 6. Testing Direct Message Sending

### Send a test message via API:

```bash
curl -X POST \
  https://your-api-id.execute-api.region.amazonaws.com/prod/send \
  -H 'x-api-key: your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "phone": "+1234567890",
    "message": "This is a test message from Daily Uplift SMS!",
    "category": "motivation"
  }'
```

## 7. Monitoring and Troubleshooting

### Check CloudWatch logs:

```bash
# Get the Lambda function name
aws cloudformation describe-stack-resources --stack-name daily-uplift-sms | grep -A 5 UpliftLambdaFunction

# View logs
aws logs get-log-events --log-group-name /aws/lambda/daily-uplift-sms-UpliftLambdaFunction --log-stream-name $(aws logs describe-log-streams --log-group-name /aws/lambda/daily-uplift-sms-UpliftLambdaFunction --order-by LastEventTime --descending --limit 1 --query 'logStreams[0].logStreamName' --output text)
```

### Check SNS delivery status:

```bash
# List SNS subscriptions
aws sns list-subscriptions-by-topic --topic-arn YOUR_SNS_TOPIC_ARN
```

## 8. Cleanup (when finished testing)

```bash
# Delete the CloudFormation stack
aws cloudformation delete-stack --stack-name daily-uplift-sms
```

Remember to replace placeholder values with actual values from your deployment.