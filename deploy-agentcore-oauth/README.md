# Amazon Bedrock AgentCore MCP Server - OAuth Deployment Guide

Complete end-to-end guide for deploying a FastMCP mathematics server to [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/) with OAuth/JWT authentication using [Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html).

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [End-to-End Deployment Flow](#end-to-end-deployment-flow)
4. [OAuth & JWT Authentication Deep Dive](#oauth--jwt-authentication-deep-dive)
5. [Testing & Accessing MCP Tools](#testing--accessing-mcp-tools)
6. [Architecture](#architecture)
7. [Troubleshooting](#troubleshooting)
8. [Production Considerations](#production-considerations)

---

## Overview

This deployment demonstrates how to secure an AgentCore MCP server using **[OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) + [OpenID Connect (OIDC)](https://openid.net/specs/openid-connect-core-1_0.html)** with Amazon Cognito as the identity provider.

### Key Features

- **OAuth Authentication**: [JWT](https://datatracker.ietf.org/doc/html/rfc7519) Bearer tokens from Amazon Cognito
- **Automatic Token Generation**: No manual token copying
- **MCP Protocol Support**: Full [Model Context Protocol](https://modelcontextprotocol.io/) implementation
- **Mathematical Operations**: Add, subtract, multiply, divide tools

### Authentication Flow

```
User Credentials → Amazon Cognito → Access Token (JWT) → Amazon Bedrock AgentCore → MCP Server
```

---

## Prerequisites

### 1. AWS Resources (Already Configured)

- **Amazon Cognito User Pool**: `your-region_XXXXXXXXX`
- **App Client**: `your-client-id` (with secret)
- **User Account**: Created in Amazon Cognito User Pool
- **[AWS Identity and Access Management (IAM)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) Roles**: Amazon Bedrock AgentCore execution role with [Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)/[AWS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) permissions

### 2. Local Tools

```bash
# Install AgentCore CLI
pip install bedrock-agentcore-starter-toolkit

# Install MCP Inspector (Node.js required)
npx @modelcontextprotocol/inspector --version

# Install Python dependencies
pip install boto3 fastmcp httpx
```

### 3. AWS CLI Configuration

```bash
aws configure
# Ensure credentials have permissions for:
# - bedrock-agentcore:*
# - cognito-idp:InitiateAuth
# - ecr:*
# - ecs:*
```

---

## End-to-End Deployment Flow

### Step 1: Understanding the MCP Server

The server (`src/agentcore_mcp.py`) uses FastMCP to implement mathematical operations:

```python
from fastmcp import FastMCP

mcp = FastMCP("Math MCP Server")

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b

# ... more tools
```

This server will be containerized and deployed to AgentCore.

### Step 2: Deploy MCP Server to AgentCore

```bash
cd infrastructure
./deploy.sh
```

**What happens during deployment while deploying agent to agentcore:**

1. **Docker Build**
   ```bash
   # Builds container with FastMCP server
   docker build --platform linux/arm64 -t maths_mcp_agentcore_oauth .
   ```

2. **[Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html) Push**
   ```bash
   # Pushes to Amazon Elastic Container Registry
   docker push account-id.dkr.ecr.region.amazonaws.com/bedrock-agentcore-maths_mcp_agentcore_oauth
   ```

3. **Amazon Bedrock AgentCore Deployment** with OAuth Configuration
   ```bash
   agentcore launch \
     --agent maths_mcp_agentcore_oauth \
     --authorizer-configuration '{
       "customJWTAuthorizer": {
         "discoveryUrl": "https://cognito-idp.region.amazonaws.com/your-region_XXXXXXXXX/.well-known/openid-configuration",
         "allowedClients": ["your-client-id"]
       }
     }'
   ```

4. **Verification**
   ```bash
   agentcore describe --agent maths_mcp_agentcore_oauth
   ```

**Expected Output:**
```
Agent ID: maths_mcp_agentcore_oauth-utG4j982PE
Agent ARN: arn:aws:bedrock-agentcore:region:account-id:runtime/maths_mcp_agentcore_oauth-xxxxx
Status: READY
```

### Step 3: Configure MCP Inspector Credentials

The MCP Inspector needs Cognito credentials to automatically generate OAuth tokens.

```bash
cd ../mcp-inspector

# Copy the template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**`.env` Configuration:**
```bash
# Cognito User Credentials
COGNITO_USERNAME=your-email@example.com
COGNITO_PASSWORD=YourPassword123#

# Cognito Configuration (replace with your values)
COGNITO_USER_POOL_ID=your-region_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret
COGNITO_REGION=your-region
```

### Step 4: Test with MCP Inspector

Launch MCP Inspector with automatic token generation:

```bash
npx @modelcontextprotocol/inspector ./start-oauth-proxy.sh
```

**What happens:**
1. Script loads credentials from `.env`
2. Calls Cognito to get fresh access token
3. Launches OAuth proxy with token
4. Opens browser at `http://localhost:6274`

**In the browser:**
- Click "Connect" to connect to the MCP server
- Click "List Tools" to see available operations
- Select a tool (e.g., `add`) and call it with parameters

---

## OAuth & JWT Authentication Deep Dive

### JWT Token Types in Cognito

Cognito issues three types of tokens during authentication:

#### 1. Access Token (✅ Used for AgentCore)

**Purpose**: API authorization
**Lifetime**: 1 hour (default)
**Key Claims**:
```json
{
  "sub": "999e9428-a021-70dc-7a98-7b8084f76f4a",
  "client_id": "your-client-id",  // ✅ REQUIRED by AgentCore
  "token_use": "access",
  "scope": "aws.cognito.signin.user.admin",
  "auth_time": 1760621310,
  "exp": 1760624910,
  "iat": 1760621310
}
```

**Note:** Access tokens do NOT have an `aud` (audience) claim.

#### 2. ID Token (❌ Not compatible with AgentCore)

**Purpose**: User identity information
**Lifetime**: 1 hour (default)
**Key Claims**:
```json
{
  "sub": "999e9428-a021-70dc-7a98-7b8084f76f4a",
  "aud": "your-client-id",  // Has aud, but...
  "token_use": "id",
  "email": "user@example.com",
  // ❌ Missing "client_id" claim required by AgentCore
}
```

#### 3. Refresh Token

**Purpose**: Obtain new access/ID tokens
**Lifetime**: 30 days (default)
**Usage**: Not used directly for API calls

### Critical OAuth Configuration Insight

**The Problem**: Amazon Cognito access tokens and ID tokens have different claims:
- Access tokens have `client_id` but **no `aud`**
- ID tokens have `aud` but **no `client_id`**

**The Solution**: Make `aud` claim optional in Amazon Bedrock AgentCore OAuth configuration.

#### Amazon Bedrock AgentCore OAuth Configuration

```json
{
  "customJWTAuthorizer": {
    "discoveryUrl": "https://cognito-idp.region.amazonaws.com/your-region_XXXXXXXXX/.well-known/openid-configuration",
    "allowedClients": ["your-client-id"]
    // ✅ allowedAudience is OMITTED - makes aud claim optional
  }
}
```

**According to [AWS Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html):**

> **JWT Claims Requirements:**
> - `client_id`: Must match one of the `allowedClients` (REQUIRED)
> - `aud`: Must match `allowedAudience` **IF SPECIFIED** (OPTIONAL)

By **removing** `allowedAudience`:
- Amazon Bedrock AgentCore only checks the `client_id` claim
- Amazon Cognito access tokens (with `client_id`) work perfectly
- No `aud` claim validation is performed

### Token Generation Flow

```
┌─────────────────────┐
│ get-token-silent.py │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────────────┐
│ Cognito InitiateAuth API    │
│ Flow: USER_PASSWORD_AUTH    │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│ Cognito Response            │
│ - Access Token (use this!)  │
│ - ID Token (don't use)      │
│ - Refresh Token (for later) │
└─────────────────────────────┘
```

### Token Validation by Amazon Bedrock AgentCore

When a request arrives with a Bearer token:

```
1. Extract token from Authorization header
   ↓
2. Fetch JWKS from discoveryUrl
   ↓
3. Verify token signature using public key
   ↓
4. Check token expiration (exp claim)
   ↓
5. Validate client_id matches allowedClients
   ↓
6. (Skip aud validation - not configured)
   ↓
7. ✅ Token valid - route request to container
```

---

## Testing & Accessing MCP Tools

### Method 1: MCP Inspector (Recommended)

**Complete workflow:**

```bash
cd mcp-inspector

# 1. Configure credentials (one time)
cp .env.example .env
nano .env  # Add your Cognito username and password

# 2. Launch MCP Inspector with automatic token generation
npx @modelcontextprotocol/inspector ./start-oauth-proxy.sh
```

**Output:**
```
Loading credentials from .env...
Getting fresh OAuth token...
✓ Token obtained successfully
Starting AgentCore OAuth MCP Proxy...
Agent ARN: arn:aws:bedrock-agentcore:ap-southeast-2:...
MCP Inspector is up and running at:
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...
```

**In the Browser:**

1. **Connect to Server**
   - Click "Connect" button
   - Status should show "Connected"

2. **List Available Tools**
   - Click "List Tools" button
   - Should see 4 tools: `add`, `subtract`, `multiply`, `divide`

3. **Call a Tool**
   ```json
   Tool: add
   Parameters: {
     "a": 5,
     "b": 3
   }

   Response: {
     "result": 8
   }
   ```

4. **Try Other Operations**
   ```json
   Tool: multiply
   Parameters: {"a": 7, "b": 6}
   Response: {"result": 42}

   Tool: divide
   Parameters: {"a": 10, "b": 2}
   Response: {"result": 5.0}
   ```

### Method 2: Secure Token Generation (Manual Testing)

If you need to obtain a token for another local tool:

```bash
cd deploy-agentcore-oauth

# Set credentials
export COGNITO_USERNAME=your-email@example.com
export COGNITO_PASSWORD='YourPassword123#'

# Generate token
python3 get-access-token.py
```

**Output:**
```
Authentication succeeded.
client_id claim present: True
aud claim present: False
expiration claim present: True
Access token written to owner-only file: .../.agentcore-access-token
```

The script deliberately does not print the token or decoded identity claims.

### Understanding the Proxy Architecture

The MCP Inspector uses a proxy to bridge the MCP protocol with Amazon Bedrock AgentCore's HTTPS+OAuth API:

```
┌──────────────────────┐
│ MCP Inspector        │
│ (Browser UI)         │
└──────────┬───────────┘
           │ stdio
           ↓
┌──────────────────────────────┐
│ start-oauth-proxy.sh         │
│ 1. Loads .env credentials    │
│ 2. Calls get-token-silent.py │
│ 3. Gets fresh OAuth token    │
│ 4. Launches proxy with token │
└──────────┬───────────────────┘
           │
           ↓
┌──────────────────────────────┐
│ agentcore-proxy-oauth.py     │
│ - Wraps MCP JSON-RPC         │
│ - Adds Authorization header  │
│ - Calls AgentCore HTTPS API  │
└──────────┬───────────────────┘
           │ HTTPS + Bearer Token
           ↓
┌──────────────────────────────┐
│ Amazon Bedrock AgentCore     │
│ - Validates JWT signature    │
│ - Checks client_id claim     │
│ - Routes to Fargate task     │
└──────────┬───────────────────┘
           │ AWS Fargate
           ↓
┌──────────────────────────────┐
│ MCP Server Container         │
│ - FastMCP framework          │
│ - Math tool implementations  │
└──────────────────────────────┘
```

**Why the proxy is needed:**
- MCP Inspector speaks the MCP protocol over stdio
- Amazon Bedrock AgentCore expects HTTPS requests with OAuth Bearer tokens
- The proxy translates between these two protocols

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                            │
│  ┌──────────────────┐         ┌─────────────────────┐       │
│  │  MCP Inspector   │         │  get-access-token   │       │
│  │  (Browser UI)    │         │  (Token Generator)  │       │
│  └────────┬─────────┘         └─────────┬───────────┘       │
└───────────┼───────────────────────────┼─────────────────────┘
            │                           │
            │ stdio                     │ Amazon Cognito API
            ↓                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      Proxy Layer                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  start-oauth-proxy.sh                                │   │
│  │  - Loads .env credentials                            │   │
│  │  - Generates fresh token via get-token-silent.py     │   │
│  │  - Launches agentcore-proxy-oauth.py with token      │   │
│  └──────────────────┬───────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────┘
                     │
                     │ HTTPS + Authorization: Bearer <token>
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                Amazon Bedrock AgentCore Runtime              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Amazon API Gateway + Lambda Authorizer              │   │
│  │  1. Extract Bearer token from Authorization header   │   │
│  │  2. Fetch JWKS from Amazon Cognito discovery URL     │   │
│  │  3. Verify JWT signature                             │   │
│  │  4. Validate exp, client_id claims                   │   │
│  │  5. Route to Fargate task                            │   │
│  └──────────────────┬───────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────┘
                     │
                     │ MCP JSON-RPC
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              [AWS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) (Amazon ECS)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Docker Container                                    │   │
│  │  - Python 3.13                                       │   │
│  │  - FastMCP framework                                 │   │
│  │  - Math tool implementations                         │   │
│  │  - MCP protocol server                               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### AWS Resources Created

| Resource | ID/ARN | Purpose |
|----------|---------|---------|
| **Agent** | `maths_mcp_agentcore_oauth-utG4j982PE` | Amazon Bedrock AgentCore runtime configuration |
| **[Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html) Repository** | `bedrock-agentcore-maths_mcp_agentcore_oauth` | Docker image storage |
| **Amazon ECS Task** | Auto-created by AgentCore | Runs MCP server container |
| **[IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) Role** | `AmazonBedrockAgentCoreSDKRuntime-*` | AgentCore execution permissions |
| **Amazon Cognito User Pool** | `your-region_XXXXXXXXX` | OAuth identity provider |
| **Amazon Cognito App Client** | `your-client-id` | OAuth client configuration |

---

## Troubleshooting

### Issue 1: 403 Forbidden - Token Rejected

**Symptoms:**
```
HTTP 403: {"message": "Forbidden"}
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Token expired (1h lifetime) | Get fresh token: `./start-oauth-proxy.sh` |
| Wrong token type (ID token instead of access) | Use access token from `get-access-token.py` |
| Token signature invalid | Check Cognito configuration matches |
| `client_id` doesn't match `allowedClients` | Verify OAuth configuration in AgentCore |

**Debug Steps:**
```bash
# Generate a fresh owner-only token file.
python3 get-access-token.py

# Use it without printing it.
agentcore invoke '{"method":"tools/list","jsonrpc":"2.0","id":1}' \
  --agent maths_mcp_agentcore_oauth \
  --bearer-token "$(< .agentcore-access-token)"
```

### Issue 2: Empty Tools List in MCP Inspector

**Symptoms:**
- MCP Inspector connects successfully
- "List Tools" returns empty array
- No error messages

**Cause:** Environment variables not passed to subprocess

**Solution:** Always use the wrapper script:
```bash
# ✅ Correct
npx @modelcontextprotocol/inspector ./start-oauth-proxy.sh

# ❌ Wrong - token not available
export BEARER_TOKEN="..."
npx @modelcontextprotocol/inspector python3 agentcore-proxy-oauth.py
```

### Issue 3: "Missing required environment variables"

**Symptoms:**
```
ERROR: COGNITO_USERNAME and COGNITO_PASSWORD environment variables must be set
```

**Solution:** Configure `.env` file:
```bash
cd mcp-inspector
cp .env.example .env
nano .env  # Add your credentials
```

### Issue 4: AgentCore Agent Not Found

**Symptoms:**
```
Agent not found: maths_mcp_agentcore_oauth
```

**Solutions:**
1. Check agent exists:
   ```bash
   agentcore list
   ```

2. Verify deployment completed:
   ```bash
   agentcore describe --agent maths_mcp_agentcore_oauth
   ```

3. If agent doesn't exist, redeploy:
   ```bash
   cd infrastructure
   ./deploy.sh
   ```

### Issue 5: Container Fails to Start

**Check container logs:**
```bash
# Get agent ARN from describe command
agentcore logs --agent maths_mcp_agentcore_oauth --follow
```

**Common issues:**
- Port 8000 not exposed in Dockerfile
- Missing Python dependencies
- Import errors in `agentcore_mcp.py`

---

## Production Considerations

### 1. Token Refresh Strategy

**Current:** Manual token refresh every hour
**Production:** Implement automatic refresh

```python
# Example: Token refresh logic
import time
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self):
        self.token = None
        self.expires_at = None

    def get_token(self):
        if self.token is None or datetime.now() >= self.expires_at:
            self.refresh_token()
        return self.token

    def refresh_token(self):
        # Call Cognito to get new token
        response = cognito_client.initiate_auth(...)
        self.token = response['AccessToken']
        # Tokens expire in 1 hour
        self.expires_at = datetime.now() + timedelta(hours=1)
```

### 2. Secure Credential Storage

**Development:** `.env` file with plaintext credentials
**Production Options:**

- **[AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)**
  ```bash
  aws secretsmanager create-secret \
    --name mcp-oauth-credentials \
    --secret-string '{"username":"user@example.com","password":"..."}'
  ```

- **[AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)**
  ```bash
  aws ssm put-parameter \
    --name /mcp/cognito/username \
    --value "user@example.com" \
    --type SecureString
  ```

### 3. Monitoring & Logging

**[Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) Metrics:**
- Token refresh success/failure rate
- API request latency
- Tool invocation counts

**Amazon CloudWatch Logs:**
```python
import logging
import watchtower

logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler())
logger.info("Tool invoked", extra={"tool": "add", "args": {"a": 5, "b": 3}})
```

### 4. Rate Limiting

**Amazon Cognito Limits:**
- InitiateAuth: 50 requests/second per account
- Implement exponential backoff for retries

**Amazon Bedrock AgentCore Limits:**
- Check AgentCore quotas in [AWS Service Quotas](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html) console
- Implement request queuing if needed

### 5. Multi-User Support

**Current:** Single user credentials in `.env`
**Production:** User-specific tokens

```python
# Store user tokens in session/database
user_tokens = {}

def get_user_token(user_id):
    if user_id not in user_tokens or token_expired(user_tokens[user_id]):
        user_tokens[user_id] = authenticate_user(user_id)
    return user_tokens[user_id]
```

### 6. Error Handling

**Implement retry logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def call_agentcore_with_retry(payload):
    response = call_agentcore(payload)
    if response.status_code == 403:
        # Token expired, refresh and retry
        refresh_token()
        raise Exception("Token expired, retrying...")
    return response
```

---

## Folder Structure

```
deploy-agentcore-oauth/
├── README.md                      # This comprehensive guide
├── .gitignore                     # Git ignore patterns
├── pyproject.toml                 # Python dependencies
├── get-access-token.py            # Secure owner-only token generator
├── .bedrock_agentcore.yaml        # AgentCore config (auto-generated)
│
├── src/
│   └── agentcore_mcp.py           # FastMCP server implementation
│
└── infrastructure/
    ├── deploy.sh                  # Deployment script with OAuth config
    └── Dockerfile                 # Container image definition

../mcp-inspector/ (shared with SigV4 deployment)
├── .env                           # OAuth credentials (gitignored)
├── .env.example                   # Template for credentials
├── get-token-silent.py            # Silent token generator for automation
├── start-oauth-proxy.sh           # Wrapper script with auto token gen
├── agentcore-proxy-oauth.py       # OAuth proxy for MCP Inspector
└── agentcore-proxy-sigv4.py       # SigV4 proxy (different deployment)
```

---

## Resources

### AWS Documentation
- [Amazon Bedrock AgentCore OAuth Authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html)
- [Amazon Bedrock AgentCore MCP Tutorial](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/01-AgentCore-runtime/02-hosting-MCP-server)
- [Amazon Cognito User Pool Authentication](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-authentication-flow.html)
- [AWS Signature Version 4 (SigV4)](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html)

### Frameworks & Tools
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)

### JWT Standards
- [RFC 7519 - JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [RFC 6749 - OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)

---

## Summary

This deployment demonstrates:

1. **OAuth 2.0 Integration**: Amazon Cognito as identity provider for Amazon Bedrock AgentCore
2. **JWT Token Management**: Understanding access tokens vs ID tokens
3. **Critical Configuration**: Making `aud` claim optional for Amazon Cognito compatibility
4. **Automated Workflow**: Automatic token generation from credentials
5. **MCP Protocol**: Full [Model Context Protocol](https://modelcontextprotocol.io/) implementation with proxying
6. **Production Patterns**: Token refresh, secure storage, monitoring

The key insight is that **Amazon Cognito access tokens work with Amazon Bedrock AgentCore when `allowedAudience` is omitted** from the OAuth configuration, making the `aud` claim optional while still requiring the `client_id` claim for authorization.
