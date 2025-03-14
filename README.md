# AWS CloudWatch Logs Analysis with Claude 3

## Overview
This project provides an automated solution for analyzing CloudWatch Logs using Amazon Bedrock's Claude 3 Sonnet model. It consists of two Lambda functions and a Step Function for orchestration. The result is stored in DynamoDB.

The solution processes logs over a 30-day period and generates comprehensive insights about system health, performance, unusual patterns, critical issues and security.

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
Requires two DynamoDB tables:
```bash
WINDOWS_TABLE = your-windows-table-name
RESULTS_TABLE = your-results-table-name
```

Lambda Configuration
Runtime: Python 3.8+

Memory: 1024 MB (minimum recommended)

Timeout: 15 minutes

Handler: lambda_function.lambda_handler

IAM Permissions
Lambda IAM Role
<details>
<summary>Click to view/copy Lambda IAM Policy</summary>

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


</details>

Step Functions Workflow
Overview
The Step Functions workflow orchestrates the log analysis process by dividing the 30-day period into manageable windows and coordinating the Lambda function executions.

State Machine Definition
<details>
<summary>Click to view/copy Step Functions State Machine</summary>

{
  "Comment": "CloudWatch Log Analysis State Machine",
  "StartAt": "Initialize",
  "States": {
    "Initialize": {
      "Type": "Pass",
      "Next": "CreateTimeWindows",
      "Parameters": {
        "execution_id.$": "$$.Execution.Id",
        "start_time.$": "$.start_time",
        "end_time.$": "$.end_time",
        "log_group_name.$": "$.log_group_name"
      }
    },
    "CreateTimeWindows": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:create-time-windows",
      "Next": "ProcessWindows",
      "Parameters": {
        "execution_id.$": "$.execution_id",
        "start_time.$": "$.start_time",
        "end_time.$": "$.end_time",
        "window_size_hours": 24
      }
    },
    "ProcessWindows": {
      "Type": "Map",
      "ItemsPath": "$.windows",
      "MaxConcurrency": 10,
      "Iterator": {
        "StartAt": "AnalyzeLogs",
        "States": {
          "AnalyzeLogs": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:analyze-cwl-logs",
            "End": true,
            "Parameters": {
              "execution_id.$": "$.execution_id",
              "window_id.$": "$.window_id",
              "log_group_name.$": "$$.Map.Item.log_group_name"
            },
            "Retry": [
              {
                "ErrorEquals": ["States.TaskFailed"],
                "IntervalSeconds": 30,
                "MaxAttempts": 3,
                "BackoffRate": 2.0
              }
            ]
          }
        }
      },
      "Next": "GenerateSummary"
    },
    "GenerateSummary": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:generate-summary",
      "End": true,
      "Parameters": {
        "execution_id.$": "$.execution_id"
      }
    }
  }
}


</details>

Deployment
Quick Setup
<details>
<summary>Click to view/copy deployment commands</summary>

# Create DynamoDB tables

aws dynamodb create-table \
    --table-name your-windows-table-name \
    --attribute-definitions \
        AttributeName=execution_id,AttributeType=S \
        AttributeName=window_id,AttributeType=S \
    --key-schema \
        AttributeName=execution_id,KeyType=HASH \
        AttributeName=window_id,KeyType=RANGE \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5

aws dynamodb create-table \
    --table-name your-results-table-name \
    --attribute-definitions \
        AttributeName=execution_id,AttributeType=S \
        AttributeName=window_id,AttributeType=S \
    --key-schema \
        AttributeName=execution_id,KeyType=HASH \
        AttributeName=window_id,KeyType=RANGE \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5

# License
This project is licensed under the MIT License - see the LICENSE file for details.
