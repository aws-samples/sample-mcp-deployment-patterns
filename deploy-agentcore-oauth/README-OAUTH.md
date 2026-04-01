# AgentCore MCP Server with OAuth Authentication

This deployment uses **OAuth/JWT authentication** with AWS Cognito for securing the AgentCore MCP server.

## Differences from SigV4 Deployment

| Feature | SigV4 (deploy-agentcore) | OAuth (deploy-agentcore-oauth) |
|---------|-------------------------|--------------------------------|
| Authentication | AWS IAM credentials | Cognito JWT tokens |
| Agent Name | `maths_mcp_agentcore` | `maths_mcp_agentcore_oauth` |
| Setup Complexity | Simple (uses AWS creds) | Complex (requires Cognito) |
| Token Type | No token needed | Bearer JWT token required |
| Best For | Internal/AWS users | External users, API access |

## Known Issue with OAuth

⚠️ **Important**: There's a known limitation with Cognito OAuth for AgentCore:

- AgentCore requires BOTH `client_id` AND `aud` claims in the JWT token
- Cognito ACCESS tokens have `client_id` but not `aud`
- Cognito ID tokens have `aud` but not `client_id`
- No single Cognito token satisfies both requirements

This is why the main deployment uses SigV4 authentication instead.

## Quick Start

### 1. Deploy with OAuth

```bash
cd infrastructure
./deploy.sh
```

### 2. Get OAuth Access Token

```bash
cd ..
./get-access-token.py
```

This will output an ACCESS token that you can use for testing.

### 3. Test with Token

```bash
agentcore invoke '{"method": "tools/list", "jsonrpc": "2.0", "id": 1}' \
  --agent maths_mcp_agentcore_oauth \
  --bearer-token YOUR_ACCESS_TOKEN
```

## Configuration

The OAuth configuration is in `infrastructure/.env`:

```bash
# OAuth Configuration
OAUTH_DISCOVERY_URL=https://cognito-idp.your-region.amazonaws.com/your-region_XXXXXXXXX/.well-known/openid-configuration
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_AUDIENCE=your-client-id
```

## Recommendation

For most use cases, we recommend using the **SigV4 deployment** (`deploy-agentcore/`) because:

1. ✅ Simpler setup (uses existing AWS credentials)
2. ✅ No token expiration issues
3. ✅ No Cognito configuration required
4. ✅ Works with existing IAM permissions

Use this OAuth deployment only if you specifically need:
- External user authentication outside AWS IAM
- API access with revocable tokens
- Integration with existing Cognito user pools
