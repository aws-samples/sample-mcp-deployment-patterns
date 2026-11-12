#!/usr/bin/env python3

"""
Test SigV4 API using Python with boto3 and requests-aws4auth
Uses default AWS credentials from ~/.aws/credentials
Following AWS documentation for HTTP API with IAM authentication
"""

import json
import os
import sys
import boto3
import requests
from requests_aws4auth import AWS4Auth

def load_env_file():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print("❌ .env file not found")
        sys.exit(1)
    
    return env_vars

def main():
    print("🔐 Testing SigV4 authenticated API Gateway with Python")
    
    # Load environment variables
    env_vars = load_env_file()
    api_url = env_vars.get('API_GATEWAY_URL')
    region = env_vars.get('REGION', 'us-west-2')
    
    if not api_url:
        print("❌ API_GATEWAY_URL not found in .env file")
        sys.exit(1)
    
    print(f"API URL: {api_url}")
    print(f"Region: {region}")
    print("")
    
    # Setup AWS authentication using default credentials
    print("📋 Setting up AWS authentication...")
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if not credentials:
            print("❌ AWS credentials not found")
            print("💡 Run 'aws configure' to set up your credentials")
            sys.exit(1)
        
        # Create AWS4Auth object
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'execute-api',
            session_token=credentials.token
        )
        
        print("✅ AWS credentials loaded successfully")
        
    except Exception as e:
        print(f"❌ Error setting up AWS authentication: {e}")
        sys.exit(1)
    
    # Test health endpoint (no authentication required)
    print("")
    print("🏥 Testing health endpoint (no authentication)...")
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Health check response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Health check failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
    
    # Test MCP tools/list endpoint
    print("")
    print("🔧 Testing MCP tools/list endpoint...")
    try:
        mcp_request = {"method": "tools/list", "id": 1}
        response = requests.post(
            f"{api_url}/mcp",
            json=mcp_request,
            auth=auth,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ MCP tools/list response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ MCP tools/list failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing MCP endpoint: {e}")
    
    # Test MCP add_numbers tool
    print("")
    print("➕ Testing MCP add_numbers tool...")
    try:
        mcp_request = {
            "method": "tools/call",
            "params": {
                "name": "add_numbers",
                "arguments": {"a": 5, "b": 3}
            },
            "id": 2
        }
        
        response = requests.post(
            f"{api_url}/mcp",
            json=mcp_request,
            auth=auth,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ MCP add_numbers response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ MCP add_numbers failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing add_numbers: {e}")
    
    print("")
    print("🎉 Python SigV4 testing complete!")
    print("")
    print("💡 Note: If tests fail with 403 Forbidden, ensure your AWS user/role has")
    print("   the execute-api:Invoke permission for this API Gateway")

if __name__ == "__main__":
    main()
