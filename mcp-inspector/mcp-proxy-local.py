#!/usr/bin/env python3
"""
MCP Proxy Server for testing serverless MCP with authentication
"""
import asyncio
import json
import os
import sys
from mcp.server import Server
from mcp.types import Tool
import mcp.types as types
import httpx
from dotenv import load_dotenv

load_dotenv()

MCP_ENDPOINT = os.environ["MCP_ENDPOINT"]
ID_TOKEN = os.environ["ID_TOKEN"]

server = Server("maths-proxy")

async def call_serverless_mcp(method: str, params: dict = None):
    """Call the serverless MCP endpoint with authentication"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method
    }
    if params:
        payload["params"] = params
    
    headers = {
        "Authorization": f"Bearer {ID_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(MCP_ENDPOINT, json=payload, headers=headers)
        return response.json()

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Proxy tools/list to serverless MCP"""
    result = await call_serverless_mcp("tools/list")
    tools = result.get("result", {}).get("tools", [])
    
    return [
        types.Tool(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["inputSchema"]
        )
        for tool in tools
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Proxy tools/call to serverless MCP"""
    result = await call_serverless_mcp("tools/call", {
        "name": name,
        "arguments": arguments
    })
    
    content = result.get("result", {}).get("content", [])
    return [
        types.TextContent(type="text", text=item["text"])
        for item in content
    ]

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
