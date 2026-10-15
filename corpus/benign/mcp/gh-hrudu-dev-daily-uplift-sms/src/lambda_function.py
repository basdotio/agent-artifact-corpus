import json
import random
import boto3
import os
import logging
from datetime import datetime
import pytz
import boto3.dynamodb.conditions as conditions

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

def get_ist_time():
    """Get current time in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

# Message categories with their respective messages
MESSAGES = {
    "motivation": [
        "You are capable of amazing things. Keep going!",
        "Small steps forward are still progress. Celebrate them!",
        "Today is a new opportunity to create positive change.",
        "You've overcome difficult things before, and you can do it again.",
        "You are stronger than you think and braver than you believe.",
        "Don't forget to celebrate your small victories today.",
        "Your best is enough, and it will always be enough.",
        "Every challenge is an opportunity to grow stronger.",
        "Believe in yourself - you have everything you need to succeed.",
        "Your dreams are valid and worth pursuing."
    ],
    "mental_health": [
        "Your mental health matters. Be kind to yourself today.",
        "It's okay to ask for help when you need it.",
        "Your feelings are valid, but they don't define you.",
        "Self-care isn't selfish, it's necessary.",
        "Your worth isn't measured by your productivity.",
        "Healing isn't linear, and that's perfectly normal.",
        "You matter, even on the days when you don't feel like you do.",
        "Taking breaks is part of taking care of yourself.",
        "You're doing better than you think you are.",
        "It's okay to not be okay sometimes."
    ],
    "mindfulness": [
        "Take a moment to breathe deeply and appreciate this moment.",
        "You don't have to be perfect to be worthy of love and respect.",
        "Remember to drink water and take short breaks throughout your day.",
        "Progress isn't always visible, but that doesn't mean it's not happening.",
        "Be proud of yourself for making it this far.",
        "It's okay to set boundaries that protect your peace.",
        "Focus on what you can control and let go of what you can't.",
        "Every breath is a new beginning.",
        "You are exactly where you need to be right now."
    ],
    "encouragement": [
        "You're making a difference, even when you can't see it.",
        "Your kindness creates ripples of positivity.",
        "Someone believes in you today.",
        "You have survived 100% of your difficult days so far.",
        "Your story isn't over yet - keep writing."
    ]
}

def get_subscribers_preferences():
    """
    Get all subscribers and their preferences from DynamoDB
    """
    try:
        table = dynamodb.Table(SUBSCRIBERS_TABLE)
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error getting subscribers: {str(e)}")
        return []

def record_analytics(message_id, category, subscriber_count):
    """
    Record message delivery analytics
    """
    try:
        if ANALYTICS_TABLE:
            table = dynamodb.Table(ANALYTICS_TABLE)
            table.put_item(Item={
                'message_id': message_id,
                'timestamp': get_ist_time().isoformat(),
                'category': category,
                'subscriber_count': subscriber_count
            })
    except Exception as e:
        logger.error(f"Error recording analytics: {str(e)}")

def lambda_handler(event, context):
    try:
        # Check if this is a direct API call with specific parameters
        if event.get('httpMethod') == 'POST' and 'body' in event:
            body = json.loads(event['body'])
            phone = body.get('phone')
            category = body.get('category', 'motivation')
            
            # Get a single subscriber's preferences
            if SUBSCRIBERS_TABLE:
                table = dynamodb.Table(SUBSCRIBERS_TABLE)
                subscriber = table.get_item(Key={'phone_number': phone}).get('Item')
                if not subscriber:
                    return {
                        'statusCode': 404,
                        'body': json.dumps('Subscriber not found')
                    }
                
                # Override category if specified in request
                if 'category' in body:
                    category = body['category']
                else:
                    # Use subscriber's preferred category if available
                    category = subscriber.get('preferred_category', 'motivation')
            
            # Select a random message from the specified category
            if category in MESSAGES:
                message = random.choice(MESSAGES[category])
            else:
                # Fallback to motivation if category not found
                message = random.choice(MESSAGES['motivation'])
            
            # Send to a specific subscriber
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
            
            logger.info(f"Message sent to {phone}: {response['MessageId']}")
            return {
                'statusCode': 200,
                'body': json.dumps('Message sent successfully!')
            }
        
        # Regular scheduled execution - send to all subscribers
        subscribers = get_subscribers_preferences() if SUBSCRIBERS_TABLE else []
        
        if subscribers:
            # Send personalized messages based on preferences
            for subscriber in subscribers:
                phone = subscriber['phone_number']
                category = subscriber.get('preferred_category', 'motivation')
                
                # Select message based on preferred category
                if category in MESSAGES and MESSAGES[category]:
                    message = random.choice(MESSAGES[category])
                else:
                    # Fallback to random category
                    random_category = random.choice(list(MESSAGES.keys()))
                    message = random.choice(MESSAGES[random_category])
                    category = random_category
                
                # Send personalized message
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
                logger.info(f"Personalized message sent to {phone}: {response['MessageId']}")
                
                # Record analytics
                record_analytics(response['MessageId'], category, 1)
        else:
            # No subscribers in DynamoDB or table not configured, use SNS topic
            # Select a random category and message
            category = random.choice(list(MESSAGES.keys()))
            message = random.choice(MESSAGES[category])
            
            # Publish to SNS topic
            response = sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject='Daily Uplift',
                MessageAttributes={
                    'SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            
            logger.info(f"Message sent to topic: {response['MessageId']}")
            
            # Record analytics
            record_analytics(response['MessageId'], category, 0)  # 0 means unknown count
        
        return {
            'statusCode': 200,
            'body': json.dumps('Daily messages sent successfully!')
        }
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
