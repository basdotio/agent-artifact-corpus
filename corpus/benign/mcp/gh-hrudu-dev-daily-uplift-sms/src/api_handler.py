import json
import boto3
import os
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

# Get environment variables
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
SUBSCRIBERS_TABLE = os.environ.get('SUBSCRIBERS_TABLE')
ANALYTICS_TABLE = os.environ.get('ANALYTICS_TABLE')

def get_subscribers():
    """
    Get all subscribers from DynamoDB
    """
    try:
        table = dynamodb.Table(SUBSCRIBERS_TABLE)
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error getting subscribers: {str(e)}")
        return []

def get_analytics(days=30):
    """
    Get analytics data from DynamoDB
    """
    try:
        table = dynamodb.Table(ANALYTICS_TABLE)
        response = table.scan()
        items = response.get('Items', [])
        
        # Process analytics data
        category_counts = {}
        daily_counts = {}
        
        for item in items:
            # Count by category
            category = item.get('category', 'unknown')
            if category in category_counts:
                category_counts[category] += 1
            else:
                category_counts[category] = 1
                
            # Count by day
            timestamp = item.get('timestamp', '')
            if timestamp:
                date = timestamp.split('T')[0]  # Extract date part
                if date in daily_counts:
                    daily_counts[date] += 1
                else:
                    daily_counts[date] = 1
        
        return {
            'category_counts': category_counts,
            'daily_counts': daily_counts,
            'total_messages': len(items)
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return {}

def manage_subscriber(data):
    """
    Add, update, or remove a subscriber
    """
    try:
        action = data.get('action')
        phone = data.get('phone')
        
        if not phone or not action:
            return {
                'success': False,
                'message': 'Missing required parameters'
            }
        
        table = dynamodb.Table(SUBSCRIBERS_TABLE)
        
        if action == 'add':
            # Subscribe to SNS
            response = sns.subscribe(
                TopicArn=SNS_TOPIC_ARN,
                Protocol='sms',
                Endpoint=phone
            )
            
            # Save to DynamoDB
            item = {
                'phone_number': phone,
                'subscription_arn': response['SubscriptionArn'],
                'active': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Add preferred category if provided
            if 'category' in data:
                item['preferred_category'] = data['category']
                
            table.put_item(Item=item)
            
            return {
                'success': True,
                'message': f'Subscriber {phone} added successfully'
            }
            
        elif action == 'update':
            # Update subscriber preferences
            update_expression = "set active = :a"
            expression_values = {':a': True}
            
            # Update category if provided
            if 'category' in data:
                update_expression += ", preferred_category = :c"
                expression_values[':c'] = data['category']
                
            table.update_item(
                Key={'phone_number': phone},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            return {
                'success': True,
                'message': f'Subscriber {phone} updated successfully'
            }
            
        elif action == 'remove':
            # Get subscription ARN
            subscriber = table.get_item(Key={'phone_number': phone}).get('Item')
            if subscriber and 'subscription_arn' in subscriber:
                # Unsubscribe from SNS
                sns.unsubscribe(SubscriptionArn=subscriber['subscription_arn'])
            
            # Mark as inactive in DynamoDB
            table.update_item(
                Key={'phone_number': phone},
                UpdateExpression="set active = :a",
                ExpressionAttributeValues={':a': False}
            )
            
            return {
                'success': True,
                'message': f'Subscriber {phone} removed successfully'
            }
        
        return {
            'success': False,
            'message': 'Invalid action'
        }
    except Exception as e:
        logger.error(f"Error managing subscriber: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }

def send_message(data):
    """
    Send a message to a specific subscriber
    """
    try:
        phone = data.get('phone')
        message = data.get('message')
        category = data.get('category', 'custom')
        
        if not phone or not message:
            return {
                'success': False,
                'message': 'Missing required parameters'
            }
        
        # Send the message
        response = sns.publish(
            PhoneNumber=phone,
            Message=message,
            MessageAttributes={
                'SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        
        # Record analytics
        if ANALYTICS_TABLE:
            table = dynamodb.Table(ANALYTICS_TABLE)
            table.put_item(Item={
                'message_id': response['MessageId'],
                'timestamp': datetime.utcnow().isoformat(),
                'category': category,
                'subscriber_count': 1,
                'custom': True
            })
        
        return {
            'success': True,
            'message': f'Message sent to {phone} successfully',
            'message_id': response['MessageId']
        }
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }

def lambda_handler(event, context):
    """
    Handle API Gateway requests
    """
    try:
        # Get request path and method
        path = event.get('path', '')
        http_method = event.get('httpMethod', '')
        
        # Parse request body if present
        body = {}
        if 'body' in event and event['body']:
            body = json.loads(event['body'])
        
        # Handle different endpoints
        if path == '/subscribers':
            if http_method == 'GET':
                # Get all subscribers
                subscribers = get_subscribers()
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'subscribers': subscribers,
                        'count': len(subscribers)
                    })
                }
            elif http_method == 'POST':
                # Manage subscriber
                result = manage_subscriber(body)
                status_code = 200 if result['success'] else 400
                return {
                    'statusCode': status_code,
                    'body': json.dumps(result)
                }
        
        elif path == '/analytics':
            if http_method == 'GET':
                # Get analytics data
                days = event.get('queryStringParameters', {}).get('days', 30)
                try:
                    days = int(days)
                except:
                    days = 30
                    
                analytics = get_analytics(days)
                return {
                    'statusCode': 200,
                    'body': json.dumps(analytics)
                }
        
        elif path == '/send':
            if http_method == 'POST':
                # Send custom message
                result = send_message(body)
                status_code = 200 if result['success'] else 400
                return {
                    'statusCode': status_code,
                    'body': json.dumps(result)
                }
        
        # Invalid endpoint
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'Not found'})
        }
        
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': f'Error: {str(e)}'})
        }