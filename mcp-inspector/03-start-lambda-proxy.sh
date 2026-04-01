#!/bin/bash
# Wrapper script to automatically get fresh Cognito ID token and launch serverless proxy
# Credentials are loaded from .env file in deploy-serverless folder

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load environment variables from deploy-serverless/.env file
if [ -f "$SCRIPT_DIR/../deploy-serverless/.env" ]; then
    echo "Loading credentials from .env..." >&2
    export $(grep -v '^#' "$SCRIPT_DIR/../deploy-serverless/.env" | xargs)
else
    echo "ERROR: .env file not found at ../deploy-serverless/.env!" >&2
    exit 1
fi

# Generate fresh Cognito ID token
echo "Getting fresh Cognito ID token..." >&2
BEARER_TOKEN=$(python3 "$SCRIPT_DIR/get-serverless-token-silent.py")

if [ -z "$BEARER_TOKEN" ]; then
    echo "ERROR: Failed to get Cognito ID token" >&2
    exit 1
fi

echo "✓ Token obtained successfully" >&2
export BEARER_TOKEN

# Get API Gateway URL from CloudFormation stack
API_GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' --output text 2>/dev/null)
if [ -n "$API_GATEWAY_URL" ]; then
    export API_GATEWAY_URL="${API_GATEWAY_URL}/mcp"
    echo "✓ Using API Gateway URL: $API_GATEWAY_URL" >&2
else
    echo "⚠ Could not get API Gateway URL from CloudFormation, using default" >&2
fi

# Launch the serverless proxy
exec python3 "$SCRIPT_DIR/agentcore-lambda-proxy.py"
