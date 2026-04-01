# MCP Inspector Testing Guide

Test your deployed MCP servers locally using [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

## Available Proxies

### 1. Lambda Proxy (`mcp-proxy.py`)
Tests [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html) + [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) deployment with [Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html) authentication.

### 2. AgentCore Proxy (`agentcore-proxy.py`)
Tests [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/) deployment with JWT authentication.

### 3. ECS Proxy (`ecs-proxy.py`)
Tests [Amazon Elastic Container Service (ECS)](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html) + Amazon API Gateway + VPC Link deployment with JWT authentication and OAuth flow support.

### 4. EKS Proxy (`eks-proxy.py`)
Tests [Amazon Elastic Kubernetes Service (EKS)](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html) + Amazon API Gateway + VPC Link deployment with [AWS Signature Version 4 (SigV4)](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) authentication.

## Testing Lambda Deployment

### Step-by-Step Instructions

### 1. Create User and Get Amazon Cognito Token

**Create a test user:**
```bash
# Get User Pool ID from your deployment outputs
USER_POOL_ID="your-region_XXXXXXXXX"

# Create user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username testuser@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username testuser@example.com \
  --password MyPassword123! \
  --permanent
```

**Generate ID token:**
```bash
# Get App Client ID from deployment outputs
APP_CLIENT_ID="your-client-id"

# Authenticate and get tokens
aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID \
  --client-id $APP_CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=testuser@example.com,PASSWORD=MyPassword123!
```

Copy the `IdToken` from the response.

### 2. Update Proxy Configuration

Edit `mcp-proxy.py` and update the token:
```python
ID_TOKEN = "your-cognito-id-token-here"
```

### 3. Start MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Opens at: http://localhost:6274

### 4. Configure Connection

In the inspector UI, enter:
- **Transport:** stdio
- **Command:** python3  
- **Args:** `/absolute/path/to/maths/mcp-inspector/mcp-proxy.py`

### 5. Connect and Test

Click "Connect". You should see three available tools:
- `add_numbers` - Add two integers
- `multiply_numbers` - Multiply two integers  
- `greet_user` - Greet a user by name

## Testing ECS Deployment

### Architecture
```
MCP Inspector → ecs-proxy.py → Amazon API Gateway (JWT Auth) → VPC Link → Internal ALB → ECS Tasks
```

### Quick Start
```bash
./04-start-ecs-proxy.sh
```

**What it does:**
- Automatically reads Amazon Cognito credentials from `../deploy-ecs/.env`
- Gets JWT token from Amazon Cognito using stored credentials
- Starts MCP Inspector with authentication
- Handles token refresh automatically

### Manual Testing

```bash
npx @modelcontextprotocol/inspector python3 ecs-proxy.py
```

### Authentication Details

**Automatic JWT Authentication:**
- **Credentials**: Read from `../deploy-ecs/.env` file
- **Token Type**: Amazon Cognito ID Token (auto-generated)
- **Header**: `Authorization: Bearer <id_token>`
- **Validation**: Amazon API Gateway validates with Amazon Cognito User Pool
- **Refresh**: Automatic token refresh on expiry

## Testing EKS Deployment

### Architecture
```
MCP Inspector → EKS Proxy (SigV4) → Amazon API Gateway → VPC Link → Internal ALB → EKS Pods
```

### Prerequisites
1. **EKS deployment completed:**
   ```bash
   cd ../deploy-eks/deployment
   ./01-deploy-infrastructure.sh
   ./02-deploy-workload.sh
   ./03-deploy-api-gateway.sh
   ```

2. **AWS credentials configured:**
   ```bash
   aws configure
   # or ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set
   ```

3. **[AWS Identity and Access Management (IAM)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) permissions for Amazon API Gateway:**
   - The IAM policy created by the EKS deployment should be attached to your user/role
   - Policy allows `execute-api:Invoke` on the Amazon API Gateway

### Quick Start
```bash
# Start MCP Inspector with EKS proxy
./05-start-eks-proxy.sh
```

### Manual Testing
```bash
# Test health endpoint (no auth required)
curl https://YOUR_API_GATEWAY_URL/health

# Test with Python script (SigV4 auth required)
cd ../deploy-eks/deployment
python3 test-api.py

# Start MCP Inspector manually
npx @modelcontextprotocol/inspector python3 eks-proxy.py
```

### Features
- **Authentication**: [AWS SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) (IAM-based)
- **Health Check**: Public endpoint for monitoring
- **MCP Endpoints**: Authenticated via IAM
- **Security**: VPC Link ensures private connectivity
- **Scalability**: Kubernetes horizontal pod autoscaling

### Troubleshooting

**Error: API_GATEWAY_URL not found**
```bash
# Run the API Gateway deployment
cd ../deploy-eks/deployment
./03-deploy-api-gateway.sh
```

**Error: 403 Forbidden**
```bash
# Attach the IAM policy to your user/role
aws iam attach-user-policy --user-name YOUR_USERNAME --policy-arn POLICY_ARN
```

**Error: Health check failed**
```bash
# Check Amazon API Gateway status
aws apigatewayv2 get-apis --region us-west-2
```

## Testing Amazon Bedrock AgentCore Deployment

### Step-by-Step Instructions

### 1. Get JWT Token for Amazon Bedrock AgentCore

**Create AgentCore test user:**
```bash
# Create user for AgentCore client
aws cognito-idp admin-create-user \
  --user-pool-id your-region_XXXXXXXXX \
  --username agentcore-test@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS \
  --region your-region

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id your-region_XXXXXXXXX \
  --username agentcore-test@example.com \
  --password AgentCore123! \
  --permanent \
  --region your-region
```

**Generate JWT token:**
```bash
# Get JWT token for AgentCore client
aws cognito-idp admin-initiate-auth \
  --user-pool-id your-region_XXXXXXXXX \
  --client-id your-client-id \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=agentcore-test@example.com,PASSWORD=AgentCore123! \
  --region your-region
```

Copy the `IdToken` from the response.

### 2. Update AgentCore Proxy

Edit `agentcore-proxy.py` and update the JWT token:
```python
JWT_TOKEN = "your-jwt-id-token-here"
```

### 3. Start MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

### 4. Configure Connection

In the inspector UI, enter:
- **Transport:** stdio
- **Command:** python3  
- **Args:** `/absolute/path/to/maths/mcp-inspector/agentcore-proxy.py`

### 5. Connect and Test

Click "Connect". You should see the same three tools connecting to Amazon Bedrock AgentCore.

## Test Examples

**Add Numbers:**
```json
{"name": "add_numbers", "arguments": {"a": 5, "b": 3}}
```
Expected result: `8`

**Multiply Numbers:**
```json
{"name": "multiply_numbers", "arguments": {"a": 4, "b": 7}}
```
Expected result: `28`

**Greet User:**
```json
{"name": "greet_user", "arguments": {"name": "Alice"}}
```
Expected result: `Hello, Alice! Nice to meet you.`

## Architecture Comparison

**Lambda Flow:**
```
MCP Inspector → mcp-proxy.py → Amazon API Gateway + Amazon Cognito → AWS Lambda → MCP Server
```

**AgentCore Flow:**
```
MCP Inspector → agentcore-proxy.py → Amazon Bedrock AgentCore Runtime → MCP Server
```

**ECS Flow:**
```
MCP Inspector → ecs-proxy.py → Amazon API Gateway (JWT) → VPC Link → Internal ALB → ECS → MCP Server
```

## Troubleshooting

**Connection Error:**
- Use `python3` not `python`
- Use absolute path to proxy files
- Check tokens haven't expired

**HTTP 401 - Unauthorized:**
- Get fresh Amazon Cognito ID token
- Update token in proxy file
- Verify user exists and password is correct

**"spawn python ENOENT":**
- Change command to `python3`

**Amazon Bedrock AgentCore 403 Forbidden:**
- This is expected without JWT token
- Ensure JWT token is valid and not expired
- Check OAuth configuration

**ECS Authentication Issues:**
- Check Amazon Cognito credentials in `../deploy-ecs/.env`
- Verify `COGNITO_USERNAME` and `COGNITO_PASSWORD` are correct
- Ensure `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET` are set
- Check Amazon API Gateway URL is correct in `API_GATEWAY_URL`

## Kill MCP Inspector

To stop the inspector:

```bash
# Kill inspector process
pkill -f "mcp.*inspector"

# Or just Ctrl+C in the terminal where inspector is running
```

You can also close the browser tab, but the process may continue running in the background.
