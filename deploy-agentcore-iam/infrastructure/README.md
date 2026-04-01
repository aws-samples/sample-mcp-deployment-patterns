# AgentCore MCP Deployment

Deploy the Math MCP server to Amazon Bedrock AgentCore Runtime with OAuth authentication.

## Architecture

```
Client → AgentCore Runtime → MCP Server (Container)
```

## Prerequisites

- AWS CLI configured
- Python 3.10+
- AgentCore CLI: `pip install bedrock-agentcore-starter-toolkit`

## Quick Start

### 1. Deploy to AgentCore

```bash
cd deploy-agentcore
./deploy.sh
```

### 2. Test with JWT Authentication

```bash
# Get JWT token first (see Authentication section)
JWT_TOKEN="your-jwt-token" ./test-agentcore.sh
```

## Authentication Setup

### OAuth Configuration

The deployment uses Cognito OAuth with these details:
- **User Pool:** `ap-southeast-2_GWXR6uLu0`
- **Client ID:** `7al5frtggpvvlthpc2no59a773`
- **Discovery URL:** `https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_GWXR6uLu0/.well-known/openid-configuration`

### Create Test User & Get JWT Token

```bash
# Create user
aws cognito-idp admin-create-user \
  --user-pool-id ap-southeast-2_GWXR6uLu0 \
  --username testuser@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS \
  --region ap-southeast-2

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-southeast-2_GWXR6uLu0 \
  --username testuser@example.com \
  --password MyPassword123! \
  --permanent \
  --region ap-southeast-2

# Get JWT token
aws cognito-idp admin-initiate-auth \
  --user-pool-id ap-southeast-2_GWXR6uLu0 \
  --client-id 7al5frtggpvvlthpc2no59a773 \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=testuser@example.com,PASSWORD=MyPassword123! \
  --region ap-southeast-2
```

Copy the `IdToken` from the response.

## Deployment Details

**Successful Deployment:**
- **Agent ARN:** `arn:aws:bedrock-agentcore:ap-southeast-2:615574357756:runtime/maths_mcp_agentcore-8gFzh4CUpZ`
- **Endpoint ARN:** `arn:aws:bedrock-agentcore:ap-southeast-2:615574357756:runtime/maths_mcp_agentcore-8gFzh4CUpZ/runtime-endpoint/DEFAULT`
- **Status:** READY
- **Region:** ap-southeast-2

## Testing

### Test Commands

```bash
# List tools
agentcore invoke '{"method": "tools/list", "jsonrpc": "2.0", "id": 1}' \
  --agent maths_mcp_agentcore \
  --bearer-token YOUR_JWT_TOKEN

# Add numbers
agentcore invoke '{"method": "tools/call", "params": {"name": "add_numbers", "arguments": {"a": 5, "b": 3}}, "jsonrpc": "2.0", "id": 1}' \
  --agent maths_mcp_agentcore \
  --bearer-token YOUR_JWT_TOKEN

# Multiply numbers
agentcore invoke '{"method": "tools/call", "params": {"name": "multiply_numbers", "arguments": {"a": 4, "b": 7}}, "jsonrpc": "2.0", "id": 1}' \
  --agent maths_mcp_agentcore \
  --bearer-token YOUR_JWT_TOKEN

# Greet user
agentcore invoke '{"method": "tools/call", "params": {"name": "greet_user", "arguments": {"name": "Alice"}}, "jsonrpc": "2.0", "id": 1}' \
  --agent maths_mcp_agentcore \
  --bearer-token YOUR_JWT_TOKEN
```

### Expected Behavior

- **Without JWT:** 403 Forbidden (OAuth working correctly)
- **With Valid JWT:** Successful MCP responses
- **Invalid JWT:** Authentication errors

## Available Tools

- `add_numbers(a, b)` - Add two numbers
- `multiply_numbers(a, b)` - Multiply two numbers  
- `greet_user(name)` - Greet a user by name

## Environment Variables

Configure in `.env` file:
- `AGENT_NAME` - Agent name (default: maths_mcp_agentcore)
- `REGION` - AWS region (default: ap-southeast-2)
- `OAUTH_DISCOVERY_URL` - Cognito OIDC discovery URL
- `OAUTH_CLIENT_ID` - Cognito app client ID
- `OAUTH_AUDIENCE` - OAuth audience (same as client ID)

## Monitoring & Logs

```bash
# Check agent status
agentcore status --agent maths_mcp_agentcore --verbose

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/maths_mcp_agentcore-8gFzh4CUpZ-DEFAULT --follow --region ap-southeast-2
```

## Troubleshooting

### AgentCore CLI Not Found
```bash
pip install bedrock-agentcore-starter-toolkit
```

### 403 Forbidden Error
- This is expected without JWT token
- Ensure JWT token is valid and not expired
- Check OAuth configuration matches Cognito setup

### Authentication Issues
- Verify Cognito user exists and password is set
- Check client ID and discovery URL in `.env`
- Ensure auth flow `ADMIN_NO_SRP_AUTH` is enabled on client

### Configuration Issues
```bash
agentcore configure list
agentcore status --agent maths_mcp_agentcore --verbose
```
