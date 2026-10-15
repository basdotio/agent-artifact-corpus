#!/usr/bin/env python3
import boto3
import argparse
import sys

def subscribe_phone_number(topic_arn, phone_number):
    """
    Subscribe a phone number to the SNS topic
    """
    try:
        sns = boto3.client('sns')
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='sms',
            Endpoint=phone_number
        )
        print(f"Successfully subscribed {phone_number} to Daily Uplift SMS!")
        print(f"Subscription ARN: {response['SubscriptionArn']}")
        return True
    except Exception as e:
        print(f"Error subscribing {phone_number}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Subscribe a phone number to Daily Uplift SMS')
    parser.add_argument('--topic-arn', required=True, help='SNS Topic ARN')
    parser.add_argument('--phone', required=True, help='Phone number with country code (e.g., +12345678901)')
    
    args = parser.parse_args()
    
    # Validate phone number format (basic check)
    if not args.phone.startswith('+'):
        print("Error: Phone number must include country code and start with '+' (e.g., +12345678901)")
        sys.exit(1)
    
    success = subscribe_phone_number(args.topic_arn, args.phone)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
