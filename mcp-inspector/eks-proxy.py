#!/usr/bin/env python3
"""
MCP Inspector Proxy for EKS Deployment
Connects MCP Inspector to EKS-deployed MCP server via API Gateway with AWS SigV4 authentication
"""

import json
import sys
import asyncio
import os
import boto3
from pathlib import Path
from dotenv import load_dotenv
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import httpx
import uuid
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    INVALID_REQUEST,
    INTERNAL_ERROR
)

# Load environment variables from deploy-eks/.env
env_path = Path(__file__).parent.parent / 'deploy-eks' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}. Using environment variables or defaults.", file=sys.stderr)

# EKS Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")
REGION = os.getenv("REGION", "us-west-2")

if not API_GATEWAY_URL:
    print("Error: API_GATEWAY_URL not found in .env file", file=sys.stderr)
    print("Please run the EKS deployment first: cd deploy-eks/deployment && ./03-deploy-api-gateway.sh", file=sys.stderr)
    sys.exit(1)

# Create MCP server instance
server = Server("eks-mcp-proxy")

# Generate a session ID for this MCP Inspector session
SESSION_ID = str(uuid.uuid4())

# Get AWS credentials
session = boto3.Session()
credentials = session.get_credentials()

if not credentials:
    print("Error: AWS credentials not found", file=sys.stderr)
    print("Please configure AWS credentials: aws configure", file=sys.stderr)
    sys.exit(1)

async def call_eks_api(endpoint, payload=None):
    """Call EKS API Gateway with AWS SigV4 authentication"""
    try:
        url = f"{API_GATEWAY_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        
        if payload:
            # POST request for MCP calls
            body = json.dumps(payload).encode('utf-8')
            method = 'POST'
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'x-mcp-session-id': SESSION_ID
            }
        else:
            # GET request for health check
            body = b''
            method = 'GET'
            headers = {
                'Accept': 'application/json',
                'x-mcp-session-id': SESSION_ID
            }

        # Create AWS request for signing
        request = AWSRequest(
            method=method,
            url=url,
            data=body,
            headers=headers
        )

        # Sign the request with SigV4
        SigV4Auth(credentials, 'execute-api', REGION).add_auth(request)

        # Extract signed headers
        signed_headers = dict(request.headers)

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == 'POST':
                response = await client.post(url, content=body, headers=signed_headers)
            else:
                response = await client.get(url, headers=signed_headers)
            
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        import traceback
        error_details = f"HTTP {e.response.status_code}: {e.response.text}\n{traceback.format_exc()}"
        print(f"EKS API Gateway HTTP Error: {error_details}", file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", 1) if payload else 1,
            "error": {
                "code": INTERNAL_ERROR,
                "message": f"EKS API Gateway request failed: {error_details}"
            }
        }
    except Exception as e:
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"EKS API Gateway Error: {error_details}", file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", 1) if payload else 1,
            "error": {
                "code": INTERNAL_ERROR,
                "message": f"EKS API Gateway request failed: {error_details}"
            }
        }

async def test_health():
    """Test the health endpoint (no authentication required)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_GATEWAY_URL}/health")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return None

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools from EKS MCP server"""
    try:
        response = await call_eks_api("mcp", {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        })

        if "result" in response and "tools" in response["result"]:
            return [
                Tool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    inputSchema=tool.get("inputSchema", {})
                )
                for tool in response["result"]["tools"]
            ]
        return []

    except Exception as e:
        print(f"Error listing tools: {e}", file=sys.stderr)
        return []

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Proxy tools/call to EKS MCP server"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": arguments
        }
    }

    response = await call_eks_api("mcp", payload)

    if "error" in response:
        return [TextContent(type="text", text=f"Error: {response['error']['message']}")]

    # Extract result from MCP server response
    if "result" in response and "content" in response["result"]:
        content_list = []
        for content in response["result"]["content"]:
            content_list.append(TextContent(type="text", text=content["text"]))
        return content_list

    return [TextContent(type="text", text="No response from EKS MCP server")]

async def main():
    # Test health endpoint first
    print(f"Testing EKS MCP server health...", file=sys.stderr)
    health = await test_health()
    if health:
        print(f"✅ Health check passed: {health}", file=sys.stderr)
    else:
        print(f"⚠️  Health check failed, but continuing...", file=sys.stderr)

    # Run the server using stdin/stdout
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    print(f"Starting EKS MCP Proxy with SigV4 authentication", file=sys.stderr)
    print(f"API Gateway URL: {API_GATEWAY_URL}", file=sys.stderr)
    print(f"Session ID: {SESSION_ID}", file=sys.stderr)
    print(f"Region: {REGION}", file=sys.stderr)
    asyncio.run(main())