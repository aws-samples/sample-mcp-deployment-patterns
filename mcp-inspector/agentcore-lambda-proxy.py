#!/usr/bin/env python3
"""
MCP Inspector Proxy for Serverless Lambda with Cognito Authentication
Connects MCP Inspector to Lambda API Gateway using HTTPS endpoint with JWT Bearer token (ID token)
"""

import json
import sys
import asyncio
import os
import httpx
import uuid
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    INVALID_REQUEST,
    INTERNAL_ERROR
)

# Serverless Lambda Configuration - get from environment or use default
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL')
REGION = os.getenv('REGION')

# Cognito ID Token - Get this from get-access-token.py (returns ID token now)
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
if not BEARER_TOKEN:
    print("ERROR: BEARER_TOKEN environment variable not set", file=sys.stderr)
    print("This should be set automatically by 03-start-lambda-proxy.sh", file=sys.stderr)
    sys.exit(1)

# Create MCP server instance
server = Server("serverless-mcp-proxy")

# Generate a session ID for this MCP Inspector session
SESSION_ID = str(uuid.uuid4())

async def call_serverless(payload):
    """Call Serverless Lambda using API Gateway with Cognito ID token authentication"""
    try:
        # Prepare the request body
        body = json.dumps(payload)

        # Cognito authentication headers
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                API_GATEWAY_URL,
                content=body,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error calling Serverless Lambda: {type(e).__name__}: {e}", file=sys.stderr)
        raise

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools from Serverless Lambda"""
    try:
        # Call Lambda to get tools list
        response = await call_serverless({
            "method": "tools/list",
            "jsonrpc": "2.0",
            "id": 1
        })

        # Extract tools from response
        if "result" in response and "tools" in response["result"]:
            tools_data = response["result"]["tools"]
            return [
                Tool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    inputSchema=tool.get("inputSchema", {})
                )
                for tool in tools_data
            ]
        return []

    except Exception as e:
        print(f"Error listing tools: {e}", file=sys.stderr)
        return []

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Call a tool on Serverless Lambda"""
    try:
        # Call Lambda to execute the tool
        response = await call_serverless({
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            },
            "jsonrpc": "2.0",
            "id": 1
        })

        # Extract result from response
        if "result" in response:
            result = response["result"]
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    text = content[0].get("text", str(result))
                else:
                    text = str(content)
            else:
                text = str(result)

            return [TextContent(type="text", text=text)]

        # Handle error response
        if "error" in response:
            error = response["error"]
            error_msg = f"Error: {error.get('message', 'Unknown error')}"
            return [TextContent(type="text", text=error_msg)]

        return [TextContent(type="text", text=str(response))]

    except Exception as e:
        error_msg = f"Error calling tool '{name}': {type(e).__name__}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [TextContent(type="text", text=error_msg)]

async def main():
    """Main entry point"""
    from mcp.server.stdio import stdio_server

    print(f"Starting Serverless Lambda MCP Proxy...", file=sys.stderr)
    print(f"API Gateway URL: {API_GATEWAY_URL}", file=sys.stderr)
    print(f"Session ID: {SESSION_ID}", file=sys.stderr)
    print(f"Using Cognito ID Token authentication", file=sys.stderr)
    print(f"", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
