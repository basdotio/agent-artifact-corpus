import json
import boto3
import os
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Handle requests for the static website
    """
    try:
        # Get the requested path
        path = event.get('path', '')
        
        # Default to index.html if root path
        if path == '/' or path == '':
            path = '/index.html'
            
        # Map file extensions to content types
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon'
        }
        
        # Determine content type based on file extension
        file_ext = os.path.splitext(path)[1]
        content_type = content_types.get(file_ext, 'text/plain')
        
        # Read the file from the static directory
        file_path = os.path.join(os.path.dirname(__file__), 'static', path.lstrip('/'))
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                
            # Return the file content
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': content_type
                },
                'body': content.decode('utf-8') if content_type.startswith('text/') or content_type == 'application/javascript' or content_type == 'application/json' else base64.b64encode(content).decode('utf-8'),
                'isBase64Encoded': not (content_type.startswith('text/') or content_type == 'application/javascript' or content_type == 'application/json')
            }
        except FileNotFoundError:
            # Return 404 if file not found
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'text/plain'
                },
                'body': 'File not found'
            }
            
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'text/plain'
            },
            'body': f'Error: {str(e)}'
        }