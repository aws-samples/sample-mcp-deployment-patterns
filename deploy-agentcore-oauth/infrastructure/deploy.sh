#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load environment variables
if [ -f ../.env ]; then
    print_status "Loading environment variables from .env file..."
    export $(grep -v '^#' ../.env | xargs)
else
    print_error ".env file not found. Please create one with required variables."
    exit 1
fi

# Configuration
AGENT_NAME=${AGENT_NAME:-maths_mcp_agentcore_oauth}
REGION=${REGION:-ap-southeast-2}
# Get absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENTRYPOINT="$PROJECT_DIR/src/agentcore_mcp.py"
REQUIREMENTS_FILE="$PROJECT_DIR/src/requirements.txt"

# Create OAuth config JSON
# Note: allowedAudience is optional. Removing it allows Cognito ACCESS tokens
# (which have client_id but not aud) to work. According to AWS AgentCore OAuth docs:
# client_id: Must match one of the allowedClients (REQUIRED)
# aud: Must match allowedAudience IF SPECIFIED (OPTIONAL)
OAUTH_CONFIG="{\"customJWTAuthorizer\":{\"discoveryUrl\":\"$OAUTH_DISCOVERY_URL\",\"allowedClients\":[\"$OAUTH_CLIENT_ID\"]}}"

print_status "AgentCore Deployment Configuration:"
echo "  Agent Name: $AGENT_NAME"
echo "  Region: $REGION"
echo "  Entrypoint: $ENTRYPOINT"
echo "  OAuth Discovery URL: $OAUTH_DISCOVERY_URL"
echo "  OAuth Client ID: $OAUTH_CLIENT_ID"

# Check if AgentCore starter toolkit is installed
if ! command -v agentcore &> /dev/null; then
    print_status "Installing AgentCore Starter Toolkit..."
    pip install bedrock-agentcore-starter-toolkit
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    print_error "AWS CLI is not configured or credentials are invalid"
    exit 1
fi

print_success "Agentcore configured successfully"

# Change to project directory for agentcore configure
cd "$PROJECT_DIR"

# Configure the agent with OAuth authentication
print_status "Configuring AgentCore agent with OAuth authentication..."
printf "\n\nyes\n" | agentcore configure \
    --entrypoint "$ENTRYPOINT" \
    --name $AGENT_NAME \
    --region $REGION \
    --protocol MCP \
    --requirements-file "$REQUIREMENTS_FILE" \
    --authorizer-config "$OAUTH_CONFIG"

if [ $? -eq 0 ]; then
    print_success "Agent configured successfully"
else
    print_error "Agent configuration failed"
    exit 1
fi

# Deploy the agent
print_status "Deploying agent to AgentCore..."
agentcore launch --agent $AGENT_NAME

if [ $? -eq 0 ]; then
    print_success "Agent deployed successfully"
else
    print_error "Agent deployment failed"
    exit 1
fi

# Get agent status
print_status "Getting agent status..."
agentcore status --agent $AGENT_NAME

print_success "Deployment completed successfully!"
echo ""
echo "=== Next Steps ==="
echo "1. Test the deployment:"
echo "   agentcore invoke '{\"method\": \"tools/list\", \"jsonrpc\": \"2.0\", \"id\": 1}' --agent $AGENT_NAME"
echo ""
echo "2. Test with JWT authentication:"
echo "   agentcore invoke '{\"method\": \"tools/call\", \"params\": {\"name\": \"add_numbers\", \"arguments\": {\"a\": 5, \"b\": 3}}, \"jsonrpc\": \"2.0\", \"id\": 1}' --agent $AGENT_NAME --bearer-token YOUR_JWT_TOKEN"
echo ""
echo "3. Check logs:"
echo "   agentcore status --agent $AGENT_NAME --verbose"
