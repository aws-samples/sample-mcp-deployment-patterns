#!/usr/bin/env python3
"""
AgentCore MCP Server for Math Operations
Standard MCP server that works with Bedrock AgentCore Runtime
"""

from mcp.server.fastmcp import FastMCP

# Create FastMCP server instance for AgentCore
# host="0.0.0.0" binds to all interfaces (required for container)
# stateless_http=True enables stateless mode (required for AgentCore)
mcp = FastMCP("maths", host="0.0.0.0", stateless_http=True)  # nosec B104 - binding to all interfaces required for AgentCore Fargate container

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers together"""
    return a * b

@mcp.tool()
def greet_user(name: str) -> str:
    """Greet a user by name"""
    return f"Hello, {name}! Nice to meet you."

# Auto-run with streamable-http transport for AgentCore
mcp.run(transport="streamable-http")
