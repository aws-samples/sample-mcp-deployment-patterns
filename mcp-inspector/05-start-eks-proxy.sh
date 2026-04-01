#!/bin/bash

# Start EKS MCP Proxy for MCP Inspector
# This script starts the EKS proxy with SigV4 authentication

set -e

echo "🚀 Starting EKS MCP Proxy for MCP Inspector"
echo "==========================================="

# Check if .env file exists
if [ ! -f "../deploy-eks/.env" ]; then
    echo "❌ Error: .env file not found at ../deploy-eks/.env"
    echo "💡 Please run the EKS deployment first:"
    echo "   cd ../deploy-eks/deployment"
    echo "   ./01-deploy-infrastructure.sh"
    echo "   ./02-deploy-workload.sh"
    echo "   ./03-deploy-api-gateway.sh"
    exit 1
fi

# Load environment variables to check configuration
source ../deploy-eks/.env

if [ -z "$API_GATEWAY_URL" ]; then
    echo "❌ Error: API_GATEWAY_URL not found in .env file"
    echo "💡 Please run the API Gateway deployment:"
    echo "   cd ../deploy-eks/deployment"
    echo "   ./03-deploy-api-gateway.sh"
    exit 1
fi

echo "📋 Configuration:"
echo "   API Gateway URL: $API_GATEWAY_URL"
echo "   Region: $REGION"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ Error: AWS credentials not configured"
    echo "💡 Please configure AWS credentials:"
    echo "   aws configure"
    exit 1
fi

echo "✅ AWS credentials configured"

# Test API Gateway health endpoint
echo "🏥 Testing API Gateway health endpoint..."
if curl -s "$API_GATEWAY_URL/health" >/dev/null; then
    echo "✅ API Gateway health check passed"
else
    echo "⚠️  API Gateway health check failed, but continuing..."
fi

echo ""
echo "🎯 Starting MCP Inspector with EKS proxy..."
echo "💡 This will connect MCP Inspector to your EKS-deployed MCP server"
echo ""

# Start MCP Inspector with the EKS proxy
npx @modelcontextprotocol/inspector python3 eks-proxy.py