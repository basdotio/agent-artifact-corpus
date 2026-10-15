#!/usr/bin/env python3
import boto3
import argparse
import sys
import json

def subscribe_phone_number(topic_arn, phone_number, preferred_category=None):
    """
    Subscribe a phone number to the SNS topic and save preferences to DynamoDB
    """
    try:
        # Subscribe to SNS
        sns = boto3.client('sns')
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='sms',
            Endpoint=phone_number
        )
        print(f"Successfully subscribed {phone_number} to Daily Uplift SMS!")
        print(f"Subscription ARN: {response['SubscriptionArn']}")
        
        # Save to DynamoDB if table name is provided
        table_name = get_subscribers_table_name()
        if table_name:
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(table_name)
            
            item = {
                'phone_number': phone_number,
                'subscription_arn': response['SubscriptionArn'],
                'active': True
            }
            
            if preferred_category:
                item['preferred_category'] = preferred_category
                
            table.put_item(Item=item)
            print(f"Subscriber preferences saved to database")
            
        return True
    except Exception as e:
        print(f"Error subscribing {phone_number}: {str(e)}")
        return False

def unsubscribe_phone_number(topic_arn, phone_number):
    """
    Unsubscribe a phone number from the SNS topic and update DynamoDB
    """
    try:
        # Find subscription ARN
        subscription_arn = find_subscription_arn(topic_arn, phone_number)
        if not subscription_arn:
            print(f"No subscription found for {phone_number}")
            return False
            
        # Unsubscribe from SNS
        sns = boto3.client('sns')
        sns.unsubscribe(SubscriptionArn=subscription_arn)
        print(f"Successfully unsubscribed {phone_number} from Daily Uplift SMS!")
        
        # Update DynamoDB if table name is provided
        table_name = get_subscribers_table_name()
        if table_name:
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(table_name)
            
            # Option 1: Delete the record
            # table.delete_item(Key={'phone_number': phone_number})
            
            # Option 2: Mark as inactive (better for analytics)
            table.update_item(
                Key={'phone_number': phone_number},
                UpdateExpression="set active = :a",
                ExpressionAttributeValues={':a': False}
            )
            print(f"Subscriber marked as inactive in database")
            
        return True
    except Exception as e:
        print(f"Error unsubscribing {phone_number}: {str(e)}")
        return False

def update_preferences(phone_number, preferred_category):
    """
    Update subscriber preferences in DynamoDB
    """
    try:
        table_name = get_subscribers_table_name()
        if not table_name:
            print("DynamoDB table name not configured")
            return False
            
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        # Update preferred category
        table.update_item(
            Key={'phone_number': phone_number},
            UpdateExpression="set preferred_category = :c",
            ExpressionAttributeValues={':c': preferred_category}
        )
        print(f"Updated preferences for {phone_number}: category={preferred_category}")
        return True
    except Exception as e:
        print(f"Error updating preferences: {str(e)}")
        return False

def find_subscription_arn(topic_arn, phone_number):
    """
    Find subscription ARN for a phone number
    """
    try:
        sns = boto3.client('sns')
        paginator = sns.get_paginator('list_subscriptions_by_topic')
        for page in paginator.paginate(TopicArn=topic_arn):
            for sub in page['Subscriptions']:
                if sub['Endpoint'] == phone_number:
                    return sub['SubscriptionArn']
        return None
    except Exception as e:
        print(f"Error finding subscription: {str(e)}")
        return None

def get_subscribers_table_name():
    """
    Get the DynamoDB table name from environment or config
    """
    # Try to get from environment
    import os
    table_name = os.environ.get('SUBSCRIBERS_TABLE')
    
    # If not in environment, try to get from config file
    if not table_name:
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                table_name = config.get('subscribers_table')
        except:
            pass
    
    return table_name

def main():
    parser = argparse.ArgumentParser(description='Manage Daily Uplift SMS subscribers')
    parser.add_argument('--action', required=True, choices=['subscribe', 'unsubscribe', 'update'], 
                        help='Action to perform')
    parser.add_argument('--topic-arn', help='SNS Topic ARN (required for subscribe/unsubscribe)')
    parser.add_argument('--phone', required=True, help='Phone number with country code (e.g., +12345678901)')
    parser.add_argument('--category', choices=['motivation', 'mental_health', 'mindfulness'], 
                        help='Preferred message category')
    
    args = parser.parse_args()
    
    # Validate phone number format
    if not args.phone.startswith('+'):
        print("Error: Phone number must include country code and start with '+' (e.g., +12345678901)")
        sys.exit(1)
    
    if args.action == 'subscribe':
        if not args.topic_arn:
            print("Error: --topic-arn is required for subscribe action")
            sys.exit(1)
        success = subscribe_phone_number(args.topic_arn, args.phone, args.category)
    elif args.action == 'unsubscribe':
        if not args.topic_arn:
            print("Error: --topic-arn is required for unsubscribe action")
            sys.exit(1)
        success = unsubscribe_phone_number(args.topic_arn, args.phone)
    elif args.action == 'update':
        if not args.category:
            print("Error: --category is required for update action")
            sys.exit(1)
        success = update_preferences(args.phone, args.category)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()