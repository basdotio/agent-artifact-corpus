#!/usr/bin/env python3
import boto3
import argparse
import sys

def unsubscribe_phone_number(topic_arn, subscription_arn):
    """
    Unsubscribe a phone number from the SNS topic
    """
    try:
        sns = boto3.client('sns')
        sns.unsubscribe(SubscriptionArn=subscription_arn)
        print(f"Successfully unsubscribed from Daily Uplift SMS!")
        return True
    except Exception as e:
        print(f"Error unsubscribing: {str(e)}")
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
        print(f"No subscription found for {phone_number}")
        return None
    except Exception as e:
        print(f"Error finding subscription: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Unsubscribe a phone number from Daily Uplift SMS')
    parser.add_argument('--topic-arn', required=True, help='SNS Topic ARN')
    parser.add_argument('--phone', required=True, help='Phone number with country code (e.g., +12345678901)')
    
    args = parser.parse_args()
    
    # Validate phone number format
    if not args.phone.startswith('+'):
        print("Error: Phone number must include country code and start with '+' (e.g., +12345678901)")
        sys.exit(1)
    
    subscription_arn = find_subscription_arn(args.topic_arn, args.phone)
    if subscription_arn:
        success = unsubscribe_phone_number(args.topic_arn, subscription_arn)
        sys.exit(0 if success else 1)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()