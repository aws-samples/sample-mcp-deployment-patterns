#!/usr/bin/env python3
"""
MCP Inspector Proxy for AgentCore with OAuth Authentication
Connects MCP Inspector to AgentCore using HTTPS endpoint with JWT Bearer token
"""

import json
import sys
import asyncio
import os
import httpx
import uuid
from pathlib import Path
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    INVALID_REQUEST,
    INTERNAL_ERROR
)

# Load environment variables from deploy-agentcore-oauth/.env
env_path = Path(__file__).parent.parent / 'deploy-agentcore-oauth' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}. Using environment variables or defaults.", file=sys.stderr)

# AgentCore Configuration
AGENT_NAME = os.getenv("AGENT_NAME", "maths_mcp_agentcore_oauth")
REGION = os.getenv("REGION", "ap-southeast-2")

# OAuth Bearer Token - Get this from get-access-token.py
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
if not BEARER_TOKEN:
    print("ERROR: BEARER_TOKEN environment variable not set", file=sys.stderr)
    print("Get a token by running: python3 ../deploy-agentcore-oauth/get-access-token.py", file=sys.stderr)
    sys.exit(1)

# Note: AGENT_RUNTIME_ARN needs to be provided by the deployment or retrieved from AWS
AGENT_RUNTIME_ARN = os.getenv("AGENT_RUNTIME_ARN", "arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-name>")

# Create MCP server instance
server = Server("agentcore-mcp-proxy-oauth")

# Generate a session ID for this MCP Inspector session
SESSION_ID = str(uuid.uuid4())

# Construct AgentCore HTTPS endpoint URL (per AWS documentation)
encoded_arn = AGENT_RUNTIME_ARN.replace(':', '%3A').replace('/', '%2F')
AGENTCORE_URL = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

async def call_agentcore(payload):
    """Call AgentCore using HTTPS endpoint with OAuth Bearer token authentication"""
    try:
        # Prepare the request body
        body = json.dumps(payload)

        # OAuth headers as per AWS documentation
        headers = {
            "authorization": f"Bearer {BEARER_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-mcp-session-id": SESSION_ID
        }

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
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error calling AgentCore: {type(e).__name__}: {e}", file=sys.stderr)
        raise

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools from AgentCore"""
    try:
        # Call AgentCore to get tools list
        response = await call_agentcore({
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
    """Call a tool on AgentCore"""
    try:
        # Call AgentCore to execute the tool
        response = await call_agentcore({
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

    print(f"Starting AgentCore OAuth MCP Proxy...", file=sys.stderr)
    print(f"Agent ARN: {AGENT_RUNTIME_ARN}", file=sys.stderr)
    print(f"AgentCore URL: {AGENTCORE_URL}", file=sys.stderr)
    print(f"Session ID: {SESSION_ID}", file=sys.stderr)
    print(f"Using OAuth Bearer Token authentication", file=sys.stderr)
    print(f"", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
