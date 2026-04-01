#!/usr/bin/env python3
"""
MCP Inspector Proxy for AgentCore
Connects MCP Inspector to AgentCore using HTTPS endpoint with AWS SigV4 authentication
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

# Load environment variables from deploy-agentcore/.env
env_path = Path(__file__).parent.parent / 'deploy-agentcore' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}. Using environment variables or defaults.", file=sys.stderr)

# AgentCore Configuration
AGENT_NAME = os.getenv("AGENT_NAME", "maths_mcp_agentcore")
REGION = os.getenv("REGION", "ap-southeast-2")

# Note: AGENT_RUNTIME_ARN needs to be provided by the deployment or retrieved from AWS
AGENT_RUNTIME_ARN = os.getenv("AGENT_RUNTIME_ARN", "arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-name>")

# Create MCP server instance
server = Server("agentcore-mcp-proxy")

# Generate a session ID for this MCP Inspector session
SESSION_ID = str(uuid.uuid4())

# Construct AgentCore HTTPS endpoint URL
encoded_arn = AGENT_RUNTIME_ARN.replace(':', '%3A').replace('/', '%2F')
AGENTCORE_URL = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

# Get AWS credentials
session = boto3.Session()
credentials = session.get_credentials()

async def call_agentcore(payload):
    """Call AgentCore using HTTPS endpoint with AWS SigV4 authentication"""
    try:
        # Prepare the request
        body = json.dumps(payload).encode('utf-8')

        # Create AWS request for signing
        request = AWSRequest(
            method='POST',
            url=AGENTCORE_URL,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
                'x-mcp-session-id': SESSION_ID
            }
        )

        # Sign the request with SigV4
        SigV4Auth(credentials, 'bedrock-agentcore', REGION).add_auth(request)

        # Extract signed headers
        headers = dict(request.headers)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                AGENTCORE_URL,
                content=body,
                headers=headers
            )
            response.raise_for_status()

            # Parse SSE response - AgentCore returns text/event-stream
            for line in response.text.split('\n'):
                if line.startswith('data: '):
                    return json.loads(line[6:])

            # Fallback to JSON if not SSE
            return response.json()

    except httpx.HTTPStatusError as e:
        import traceback
        error_details = f"HTTP {e.response.status_code}: {e.response.text}\n{traceback.format_exc()}"
        print(f"AgentCore HTTP Error: {error_details}", file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", 1),
            "error": {
                "code": INTERNAL_ERROR,
                "message": f"AgentCore request failed: {error_details}"
            }
        }
    except Exception as e:
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"AgentCore Error: {error_details}", file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", 1),
            "error": {
                "code": INTERNAL_ERROR,
                "message": f"AgentCore request failed: {error_details}"
            }
        }

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools from AgentCore"""
    try:
        response = await call_agentcore({
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
    """Proxy tools/call to AgentCore"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": arguments
        }
    }

    response = await call_agentcore(payload)

    if "error" in response:
        return [TextContent(type="text", text=f"Error: {response['error']['message']}")]

    # Extract result from AgentCore response
    if "result" in response and "content" in response["result"]:
        content_list = []
        for content in response["result"]["content"]:
            content_list.append(TextContent(type="text", text=content["text"]))
        return content_list

    return [TextContent(type="text", text="No response from AgentCore")]

async def main():
    # Run the server using stdin/stdout
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    print(f"Starting AgentCore MCP Proxy with SigV4 authentication", file=sys.stderr)
    print(f"Agent Runtime ARN: {AGENT_RUNTIME_ARN}", file=sys.stderr)
    print(f"AgentCore URL: {AGENTCORE_URL}", file=sys.stderr)
    print(f"Session ID: {SESSION_ID}", file=sys.stderr)
    print(f"Region: {REGION}", file=sys.stderr)
    asyncio.run(main())
