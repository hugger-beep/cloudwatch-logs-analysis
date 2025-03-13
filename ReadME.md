# AWS CloudWatch Logs Analysis with Claude 3

This project provides an automated solution for analyzing CloudWatch Logs using Amazon Bedrock's Claude 3 Sonnet model. It consists of two Lambda functions and a Step Function for orchestration.

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

# Components
## 1. Initializer Lambda Function
Creates time windows for log analysis

Validates input parameters

Initializes DynamoDB entries for tracking

Triggers the processor function for each window

## 2. Processor Lambda Function
Retrieves logs for specified time windows

Processes logs using Claude 3 Sonnet

Stores analysis results in DynamoDB

Handles error reporting and status updates

## 3. ## DynamoDB Tables
log-analysis-windows: Tracks analysis windows and status

log-analysis-results: Stores analysis results
