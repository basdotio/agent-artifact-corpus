# Daily Uplift SMS 🌞

**Daily Uplift SMS** is a simple, serverless application designed to promote mental well-being by delivering a daily motivational message or mental health tip to subscribers via SMS. Powered by AWS Lambda and Amazon SNS, this solution operates entirely in the cloud, is easy to scale, and requires no ongoing manual intervention.

**New Features:**
- **IST Timezone Support** - All timestamps and scheduling in Indian Standard Time
- **Web Admin Dashboard** - Manage subscribers and view analytics
- **MCP Server Integration** - Real-time monitoring and statistics
- **Message Categories** - Motivation, Mental Health, Mindfulness, and Encouragement

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [AWS Services Used](#aws-services-used)
- [Setup & Deployment](#setup--deployment)
- [Adding or Updating Messages](#adding-or-updating-messages)
- [IST Timezone Support](#ist-timezone-support)
- [MCP Server](#mcp-server)
- [Web Dashboard](#web-dashboard)
- [Customization](#customization)
- [Contributing](#contributing)
- [License](#license)

---

## Project Overview

Millions face stress and isolation daily. A simple, uplifting message can brighten someone's day or provide much-needed support. **Daily Uplift SMS** aims to make positivity accessible to everyone, no smartphone app required—just a basic phone with SMS capability.

---

## Features

- **Automatic Daily Messaging:** Sends a random motivational message or mental health tip every day.
- **Zero Maintenance:** Fully automated using serverless AWS services.
- **Scalable:** Effortlessly supports any number of subscribers.
- **Easy to Update:** Add, remove, or edit messages without downtime.
- **No App Needed:** Works with any phone capable of receiving SMS.
- **IST Timezone:** Proper Indian Standard Time support for scheduling.
- **Web Dashboard:** Admin interface for subscriber management.
- **Real-time Monitoring:** MCP server for live statistics.

---

## Architecture

```
+-----------------+           +----------------------+           +----------------------+
|                 |           |                      |           |                      |
|  Amazon Event   |  triggers |     AWS Lambda       |  invokes  |     Amazon SNS       |
|    Bridge       +---------->+   (Select Message)   +---------->+   (Send SMS to Subs) |
|  (Scheduled)    |           |                      |           |                      |
+-----------------+           +----------------------+           +----------------------+
                                                                  |
                                                                  v
                                                      +---------------------------+
                                                      |   Subscriber Phones       |
                                                      +---------------------------+
```

- **EventBridge**: Triggers Lambda function on a daily schedule.
- **Lambda**: Picks a random message and calls SNS.
- **SNS**: Publishes SMS to all subscribed phone numbers.

---

## How It Works

1. **Daily Trigger:** Amazon EventBridge invokes the Lambda function at a scheduled time each day.
2. **Message Selection:** Lambda retrieves the pool of positive messages/mental health tips, selects one at random.
3. **SMS Broadcast:** Lambda uses Amazon SNS to send the chosen message via SMS to all subscribers.
4. **Subscriber Experience:** Subscribers receive a single uplifting SMS daily—no apps, no logins, just encouragement!

---

## AWS Services Used

- **AWS Lambda:** Serverless compute to pick and send messages.
- **Amazon SNS (Simple Notification Service):** Sends SMS to subscribers.
- **Amazon EventBridge:** Schedules daily triggers for Lambda.
- **AWS SAM (Serverless Application Model):** For infrastructure as code deployment.

---

## Setup & Deployment

### Prerequisites

- AWS Account
- AWS CLI configured
- AWS SAM CLI installed
- Basic knowledge of Lambda, SNS, and EventBridge

### Steps

1. **Clone the Repository**
   ```sh
   git clone https://github.com/yourusername/daily-uplift-sms.git
   cd daily-uplift-sms
   ```

2. **Deploy the Application**
   ```sh
   cd deployment
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Subscribe Phone Numbers**
   ```sh
   aws sns subscribe --topic-arn <SNS_TOPIC_ARN> --protocol sms --notification-endpoint +1XXXXXXXXXX
   ```
   Replace `<SNS_TOPIC_ARN>` with the ARN from the deployment output and `+1XXXXXXXXXX` with the phone number.

4. **Test the Setup**
   ```sh
   aws lambda invoke --function-name daily-uplift-sms-UpliftLambdaFunction-XXXXXXXXXXXX response.json
   ```
   Replace the function name with the actual name from the deployment output.

---

## Adding or Updating Messages

Messages are organized in two ways:

**Option 1: Edit Lambda Function**
1. Edit the `MESSAGES` dictionary in `src/lambda_function.py`
2. Redeploy the application:
   ```sh
   cd deployment
   ./deploy.sh
   ```

**Option 2: Use Message Files**
1. Edit files in `messages/` directory:
   - `motivation.txt`
   - `mental_health.txt` 
   - `mindfulness.txt`
2. Each line is a separate message

---

## IST Timezone Support

The application now supports Indian Standard Time (IST) for proper scheduling:

**IST Utilities:**
```python
from ist_utils import get_ist_time, format_ist_time, is_business_hours

# Get current IST time
ist_now = get_ist_time()

# Format as readable string
time_str = format_ist_time()  # "Monday, 23 June 2025 12:43:11 IST"

# Check business hours (9 AM - 6 PM IST)
if is_business_hours():
    send_message()
```

**Lambda Environment:**
All timestamps and analytics use IST timezone automatically.

---

## MCP Server

Real-time monitoring server for development and testing:

**Start MCP Server:**
```sh
python simple-mcp.py
```

**Available Commands:**
- `time` - Get current IST time
- `stats` - Get SMS statistics
- `quit` - Exit server

**Example:**
```
> time
IST Time: Monday, 23 June 2025 12:43:11 IST

> stats
{
  "total_subscribers": 150,
  "messages_sent_today": 150,
  "categories": ["motivation", "mental_health", "mindfulness"]
}
```

---

## Web Dashboard

Admin interface for managing subscribers and viewing analytics:

**Features:**
- View subscriber statistics
- Add/remove subscribers
- Send custom messages
- View message analytics charts
- Real-time IST time display

**Access:**
1. Deploy the application
2. Open the API Gateway URL in browser
3. Or serve locally: `cd src/static && python -m http.server 8000`

---

## Customization

- **Change Frequency:** Edit the `ScheduleExpression` parameter in `deploy.sh` to change when messages are sent.
- **Personalized Messages:** Modify the Lambda function to support user preferences or custom message pools.
- **Analytics:** Add logging or integrate with CloudWatch for delivery stats.
- **Opt-In/Out:** Add API endpoints for users to subscribe/unsubscribe.

---

## Contributing

Contributions are welcome! Please open issues or pull requests to suggest improvements, new features, or additional message packs.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

**Let's brighten the world, one message at a time!**