#!/bin/bash

# ECS MCP Proxy Starter Script
# Simplified version - proxy gets JWT token automatically from .env

set -e

echo "🎯 Starting ECS MCP Proxy"
echo "========================="

# Check if we're in the right directory
if [ ! -f "../deploy-ecs/.env" ]; then
    echo "❌ Error: ../deploy-ecs/.env not found"
    echo "Please run this script from the mcp-inspector directory"
    exit 1
fi

echo "📋 ECS proxy will automatically:"
echo "   ✅ Read Cognito credentials from ../deploy-ecs/.env"
echo "   ✅ Get JWT token from Cognito"
echo "   ✅ Connect to API Gateway with authentication"
echo ""

echo "🚀 Starting MCP Inspector..."
echo ""
echo "📖 Instructions:"
echo "   1. MCP Inspector will open in your browser"
echo "   2. The proxy handles JWT authentication automatically"
echo "   3. Click 'Connect' to start testing the ECS MCP server"
echo ""

# Start MCP Inspector
npx @modelcontextprotocol/inspector python3 ecs-proxy.py