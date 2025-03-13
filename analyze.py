import boto3
import json
import os
from datetime import datetime, timedelta
import time
from botocore.config import Config
from decimal import Decimal

# Add custom JSON encoder
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(CustomJSONEncoder, self).default(obj)

# Helper function for JSON dumps with Decimal handling
def json_dumps_with_decimal(obj):
    return json.dumps(obj, cls=CustomJSONEncoder)

def get_logs(logs_client, log_group_name, start_time, end_time, max_events=10000):
    """
    Retrieve logs from CloudWatch Logs for the specified time window with pagination
    """
    log_events = []
    next_token = None
    
    # Split time window into smaller chunks if it's too large
    current_start = start_time
    chunk_size = timedelta(days=1).total_seconds() * 1000  # 1 day in milliseconds
    
    while current_start < end_time:
        chunk_end = min(current_start + chunk_size, end_time)
        
        while True:
            if next_token:
                response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=int(current_start),
                    endTime=int(chunk_end),
                    nextToken=next_token,
                    limit=max_events
                )
            else:
                response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=int(current_start),
                    endTime=int(chunk_end),
                    limit=max_events
                )
            
            log_events.extend(response['events'])
            print(f"Retrieved {len(response['events'])} logs for period {datetime.fromtimestamp(current_start/1000)} to {datetime.fromtimestamp(chunk_end/1000)}")
            
            if 'nextToken' in response:
                next_token = response['nextToken']
            else:
                break
        
        current_start = chunk_end
        next_token = None
    
    return log_events

def truncate_logs(log_events, max_chars=32000):  # Increased max_chars for larger analysis
    """
    Truncate logs to fit within Claude's token limit while keeping the most recent logs
    Also includes basic log statistics
    """
    log_texts = []
    total_length = 0
    
    # Calculate log statistics
    total_logs = len(log_events)
    if total_logs > 0:
        earliest_log = datetime.fromtimestamp(min(event['timestamp'] for event in log_events)/1000)
        latest_log = datetime.fromtimestamp(max(event['timestamp'] for event in log_events)/1000)
        time_span = latest_log - earliest_log
    else:
        time_span = timedelta(0)
        earliest_log = latest_log = datetime.now()
    
    # Add statistics header
    stats_header = (
        f"Log Analysis Statistics:\n"
        f"Total Logs: {total_logs}\n"
        f"Time Span: {time_span}\n"
        f"Period: {earliest_log.isoformat()} to {latest_log.isoformat()}\n"
        f"-------------------\n\n"
    )
    
    total_length += len(stats_header)
    log_texts.append(stats_header)
    
    # Convert logs to text format, starting from most recent
    for event in reversed(log_events):
        log_line = f"{datetime.fromtimestamp(event['timestamp']/1000).isoformat()} - {event['message']}\n"
        if total_length + len(log_line) > max_chars:
            break
        log_texts.append(log_line)
        total_length += len(log_line)
    
    # Add truncation notice if needed
    if len(log_texts) - 1 < total_logs:  # -1 for stats header
        truncation_notice = f"\n[Note: Showing {len(log_texts) - 1} of {total_logs} logs due to size limits]\n"
        log_texts.append(truncation_notice)
    
    # Reverse back to chronological order (except stats header)
    return log_texts[0] + "".join(reversed(log_texts[1:]))

def lambda_handler(event, context):
    try:
        print(f"Received event: {json_dumps_with_decimal(event)}")
        
        # Initialize AWS clients
        dynamodb = boto3.resource('dynamodb')
        windows_table = dynamodb.Table(os.environ['WINDOWS_TABLE'])
        results_table = dynamodb.Table(os.environ['RESULTS_TABLE'])
        
        # Configure boto3 client with retries and longer timeout
        config = Config(
            retries = dict(
                max_attempts = 3
            ),
            read_timeout = 900,  # 15 minutes
            connect_timeout = 900
        )
        logs_client = boto3.client('logs', config=config)
        bedrock_runtime = boto3.client('bedrock-runtime', config=config)
        
        # Get window information from DynamoDB
        window_response = windows_table.get_item(
            Key={
                'execution_id': event['execution_id'],
                'window_id': event['window_id']
            }
        )
        
        if 'Item' not in window_response:
            raise Exception(f"Window not found: {event['execution_id']}/{event['window_id']}")
        
        window = window_response['Item']
        
        # Get logs for the time window
        log_events = get_logs(
            logs_client,
            event['log_group_name'],
            int(window['start_time']),
            int(window['end_time'])
        )
        
        # Prepare and truncate logs for analysis
        log_text = truncate_logs(log_events)
        
        # Print debug information with fixed newline counting
        print(f"Processing {len(log_events)} total logs, {log_text.count(chr(10))} after truncation")
        
        # Prepare prompt for log analysis
        user_prompt = (
            "You are an expert log analyzer. Analyze these CloudWatch logs covering a 30-day period and provide a detailed summary. "
            "Focus on identifying patterns, trends, and significant changes over time. Your analysis should be in the following format:\n\n"
            
            "OVERALL HEALTH STATUS:\n"
            "- Current system health assessment\n"
            "- Key metrics overview and trends over the 30-day period\n"
            "- System stability indicators and patterns\n\n"
            
            "CRITICAL ISSUES:\n"
            "- Critical errors and their frequencies over time\n"
            "- High-priority warnings and their patterns\n"
            "- Service disruptions or failures and their timing\n\n"
            
            "PERFORMANCE METRICS:\n"
            "- Response time patterns and trends\n"
            "- Resource utilization patterns\n"
            "- Performance bottlenecks and their frequency\n"
            "- Latency issues and timing patterns\n\n"
            
            "SECURITY EVENTS:\n"
            "- Authentication patterns\n"
            "- Access violations and their timing\n"
            "- Security-related warnings and trends\n"
            "- Potential security threats and patterns\n\n"
            
            "UNUSUAL PATTERNS:\n"
            "- Unexpected behaviors and their timing\n"
            "- Anomalous events and their frequency\n"
            "- Deviations from normal patterns\n\n"
            
            "SYSTEM HEALTH INDICATORS:\n"
            "- Resource health trends\n"
            "- Service availability patterns\n"
            "- Error rates and trends over time\n\n"
            
            "RECOMMENDATIONS:\n"
            "- Immediate actions needed based on trends\n"
            "- Preventive measures for identified patterns\n"
            "- Performance optimization suggestions\n"
            "- Security improvements based on observed patterns\n\n"
            
            "LONG-TERM TRENDS:\n"
            "- Monthly patterns and cycles\n"
            "- Gradual changes or degradation\n"
            "- Capacity planning insights\n"
            "- System evolution recommendations\n\n"
            
            "LOGS TO ANALYZE:\n" + log_text
        )
        
        # Prepare request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        }
        
        print(f"Request body length: {len(json.dumps(request_body))}")
        
        # Call Bedrock with Claude model
        print("Calling Bedrock Claude model...")
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # Parse response and extract analysis
        response_body = json.loads(response['body'].read())
        analysis = response_body.get('content', [{}])[0].get('text', '')
        
        if not analysis:
            print("Warning: Empty analysis received from Claude")
            analysis = (
                "No meaningful patterns found in the logs.\n\n"
                "OVERALL HEALTH STATUS:\n- Insufficient data for health assessment\n\n"
                "CRITICAL ISSUES:\n- No critical issues detected\n\n"
                "PERFORMANCE METRICS:\n- No performance data available\n\n"
                "SECURITY EVENTS:\n- No security events detected\n\n"
                "UNUSUAL PATTERNS:\n- No unusual patterns detected\n\n"
                "SYSTEM HEALTH INDICATORS:\n- Insufficient data for health indicators\n\n"
                "RECOMMENDATIONS:\n- Implement more detailed logging\n"
                "LONG-TERM TRENDS:\n- Insufficient data for trend analysis\n"
            )
        
        print(f"Analysis length: {len(analysis)}")
        print(f"Analysis preview: {analysis[:200]}...")
        
        # Store results in DynamoDB with enhanced metadata
        try:
            timestamp = datetime.now().isoformat()
            results_item = {
                'execution_id': event['execution_id'],
                'window_id': event['window_id'],
                'start_time': str(window['start_time']),
                'end_time': str(window['end_time']),
                'log_count': len(log_events),
                'analyzed_log_count': log_text.count(chr(10)),
                'total_log_count': len(log_events),
                'analysis': analysis,
                'created_at': timestamp,
                'log_group': event['log_group_name'],
                'analysis_metadata': {
                    'sections': [
                        'OVERALL HEALTH STATUS',
                        'CRITICAL ISSUES',
                        'PERFORMANCE METRICS',
                        'SECURITY EVENTS',
                        'UNUSUAL PATTERNS',
                        'SYSTEM HEALTH INDICATORS',
                        'RECOMMENDATIONS',
                        'LONG-TERM TRENDS'
                    ],
                    'version': '2.0',
                    'analysis_timestamp': timestamp,
                    'model': 'claude-3-sonnet',
                    'time_span_days': 30
                }
            }
            
            print(f"Storing results in DynamoDB table: {os.environ['RESULTS_TABLE']}")
            print(f"Results item preview: {json_dumps_with_decimal({k: v for k, v in results_item.items() if k != 'analysis'})}")
            
            results_table.put_item(Item=results_item)
            print("Successfully stored results in DynamoDB")
            
        except Exception as db_error:
            print(f"Error storing results in DynamoDB: {str(db_error)}")
            raise
        
        # Update window status
        try:
            windows_table.update_item(
                Key={
                    'execution_id': event['execution_id'],
                    'window_id': event['window_id']
                },
                UpdateExpression="SET #status = :status, processed_at = :processed_at",
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':processed_at': timestamp
                }
            )
            print("Successfully updated window status")
            
        except Exception as update_error:
            print(f"Error updating window status: {str(update_error)}")
            raise
        
        return {
            'execution_id': event['execution_id'],
            'window_id': event['window_id'],
            'log_count': len(log_events),
            'analyzed_logs': log_text.count(chr(10)),
            'analysis_length': len(analysis),
            'analysis_sections': 8,  # Updated for new long-term trends section
            'status': 'completed'
        }
        
    except Exception as e:
        print(f"Error processing window: {str(e)}")
        print(f"Full error details: {json_dumps_with_decimal(str(e))}")
        
        # Update window status on error
        if 'windows_table' in locals() and 'event' in locals():
            try:
                error_timestamp = datetime.now().isoformat()
                windows_table.update_item(
                    Key={
                        'execution_id': event['execution_id'],
                        'window_id': event['window_id']
                    },
                    UpdateExpression="SET #status = :status, error = :error, error_at = :error_at",
                    ExpressionAttributeNames={
                        '#status': 'status'
                    },
                    ExpressionAttributeValues={
                        ':status': 'error',
                        ':error': str(e),
                        ':error_at': error_timestamp
                    }
                )
            except Exception as update_error:
                print(f"Error updating window status: {str(update_error)}")
        
        raise
