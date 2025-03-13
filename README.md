# AWS CloudWatch Logs Analysis with Claude 3

This project provides an automated solution for analyzing CloudWatch Logs using Amazon Bedrock's Claude 3 Sonnet model. It consists of two Lambda functions and a Step Function for orchestration. The result ins stored in DynamoDB.
It processes logs over a 30-day period and generates comprehensive insights about system health, performance, unusual patterns, critical issues and security.

## Architecture Overview

```ascii
┌──────────────┐     ┌─────────────┐     ┌────────────────┐
│  CloudWatch  │     │             │     │   Processor    │
│    Logs      │────▶│ Initializer │────▶│    Lambda     │
└──────────────┘     │   Lambda    │     └────────────────┘
                     └─────────────┘              │
┌──────────────┐            │                     │
│   DynamoDB   │◀───────────┴─────────────────────┘
└──────────────┘

## Features

🔍 Automated log analysis using Claude 3 Sonnet

📊 Comprehensive analysis sections including:

Overall Health Status

Critical Issues

Performance Metrics

Security Events

Unusual Patterns

System Health Indicators

Recommendations

Long-term Trends

⚡ Efficient log processing with pagination

📈 Support for 30-day analysis windows

🔄 Automatic handling of large datasets

💾 Persistent storage of analysis results

Prerequisites
AWS Account with appropriate permissions

Python 3.8 or later

AWS CLI configured

Required AWS Services:

AWS Lambda

Amazon DynamoDB

Amazon Bedrock

CloudWatch Logs

## Features

- Analyzes CloudWatch logs over extended periods (up to 30 days)
- Generates structured analysis reports with multiple sections
- Handles large log volumes with efficient pagination
- Provides statistical summaries of analyzed logs
- Stores results in DynamoDB for future reference
- Includes error handling and status tracking


## Prerequisites

- AWS Lambda environment
- Amazon Bedrock access
- DynamoDB tables for windows and results
- CloudWatch Logs access
- IAM permissions configured

## Configuration

### Environment Variables
#### Requires two DynamoDB tables.

WINDOWS_TABLE=<your-windows-table-name>
RESULTS_TABLE=<your-results-table-name>

### Lambda Configuration

- Runtime: Python 3.8+
- Memory: 1024 MB (minimum recommended)
- Timeout: 15 minutes
- Handler: lambda_function.lambda_handler

### IAM Permissions  Required

Required permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:FilterLogEvents",
                "logs:GetLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/${WINDOWS_TABLE}",
                "arn:aws:dynamodb:*:*:table/${RESULTS_TABLE}"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "arn:aws:bedrock:*:*:foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
        }
    ]
}

