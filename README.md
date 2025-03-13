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
- Analyzes up to 30 days of CloudWatch logs
- Provides detailed analysis of system health, performance, and security
- Uses Claude 3 Sonnet for advanced pattern recognition
- Stores results in DynamoDB for historical tracking
- Handles large log volumes with efficient pagination
- Includes trend analysis and recommendations

## Prerequisites
- AWS Account with appropriate permissions
- Python 3.8 or later
- AWS CLI configured
- Required AWS services:
  - AWS Lambda
  - Amazon Bedrock
  - Amazon DynamoDB
  - Amazon CloudWatch Logs


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

