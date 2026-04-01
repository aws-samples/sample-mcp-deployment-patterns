# Maths MCP Server - Serverless Deployment

A serverless deployment of the Maths [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) Server using [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html), [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html), and [Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html) for authentication.

## Architecture

- **AWS Lambda**: Hosts the MCP server logic (lightweight implementation, 1MB package)
- **Amazon API Gateway**: Provides HTTP endpoints with CORS support
- **Amazon Cognito**: User authentication with ID tokens
- **[AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)**: Infrastructure as Code deployment

## Features

The MCP server provides three mathematical tools:
- `add_numbers(a, b)`: Add two numbers together
- `multiply_numbers(a, b)`: Multiply two numbers together
- `greet_user(name)`: Greet a user by name

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.12+
- Bash shell for running deployment scripts

## Quick Start

1. **Configure deployment**:
   ```bash
   cd deploy-serverless/
   cp .env.example .env
   ```
   
   Edit `.env` with your settings:
   ```bash
   STACK_NAME=maths-mcp-server
   REGION=us-east-1
   STAGE=dev
   USER_POOL_NAME=maths-mcp-users
   APP_CLIENT_NAME=maths-mcp-client
   
   # Optional: Auto-create test user
   COGNITO_USERNAME=your-email@example.com
   COGNITO_PASSWORD=YourSecurePassword123!
   ```

2. **Deploy**:
   ```bash
   ./infrastructure/deploy.sh
   ```
   
   The script will:
   - Deploy CloudFormation stack (Lambda, API Gateway, Cognito)
   - Auto-create test user if credentials provided in `.env`
   - Display deployment outputs

## Testing

### Testing with MCP Inspector

```bash
cd ../mcp-inspector
npx @modelcontextprotocol/inspector ./03-start-lambda-proxy.sh
```

This will automatically:
- Fetch Cognito configuration from CloudFormation
- Generate authentication token
- Connect to the MCP server

### Testing with curl

#### Authentication

The API uses Cognito User Pools with **ID tokens** (not access tokens).

#### Getting an ID Token

Get values from deployment outputs, then run:

```bash
# Get CLIENT_ID and REGION from deploy.sh output
aws cognito-idp initiate-auth \
  --client-id <CLIENT_ID from deployment output> \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=user@example.com,PASSWORD=MyPass123! \
  --region <REGION from .env> \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

#### API Endpoints

**Health Check (No Auth Required):**
```bash
GET https://<API_ID>.execute-api.<REGION>.amazonaws.com/<STAGE>/
```

**MCP Endpoint (Auth Required):**
```bash
POST https://<API_ID>.execute-api.<REGION>.amazonaws.com/<STAGE>/mcp
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

#### Usage Examples

**List Available Tools:**
```bash
curl -X POST $API_URL/mcp \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**Add Numbers:**
```bash
curl -X POST $API_URL/mcp \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "add_numbers",
      "arguments": {
        "a": 5,
        "b": 3
      }
    }
  }'
```

**Multiply Numbers:**
```bash
curl -X POST $API_URL/mcp \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "multiply_numbers",
      "arguments": {
        "a": 4,
        "b": 7
      }
    }
  }'
```

**Greet User:**
```bash
curl -X POST $API_URL/mcp \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "greet_user",
      "arguments": {
        "name": "Alice"
      }
    }
  }'
```

## File Structure

```
deploy-serverless/
├── infrastructure/
│   ├── cloudformation.yaml     # CloudFormation template
│   ├── deploy.sh              # Deployment script
│   └── cleanup.sh             # Cleanup script
├── src/
│   ├── lambda_function.py     # Lambda entry point & JSON-RPC handler
│   ├── mcp_server.py         # Lightweight MCP server with @mcp.tool() decorator
│   └── requirements.txt      # Python dependencies (none needed!)
├── .env                      # Configuration (gitignored)
├── .env.example             # Template for .env file
├── .gitignore              # Ignores .env and deployment artifacts
└── README.md            # This file
```

### MCP Inspector Files

The MCP inspector is located in `../mcp-inspector/`:
```
mcp-inspector/
├── agentcore-lambda-proxy.py        # MCP proxy for serverless Lambda
├── get-serverless-token-silent.py  # Token generator (queries CloudFormation)
└── 03-start-lambda-proxy.sh        # Startup script with auto token refresh
```

## Deployment Process

The deployment script performs the following steps:

1. **Environment Setup**: Loads configuration from `.env` file
2. **AWS Validation**: Verifies AWS CLI configuration
3. **S3 Bucket**: Creates deployment bucket if needed
4. **Package Creation**: Builds Lambda deployment package with dependencies
5. **CloudFormation**: Deploys infrastructure stack
6. **Code Update**: Updates Lambda function with packaged code
7. **User Creation**: Auto-creates Cognito test user (if credentials provided in `.env`)
8. **Output Display**: Shows deployment information and testing instructions

## Security Features

- **Amazon Cognito Authentication**: All MCP endpoints require valid JWT tokens
- **CORS Support**: Proper CORS headers for web client integration
- **[AWS Identity and Access Management (IAM)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) Roles**: Least privilege access for Lambda execution
- **Encrypted Transit**: HTTPS-only Amazon API Gateway endpoints

## Monitoring and Logging

- **[Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) Logs**: Lambda function logs available in CloudWatch
- **Amazon API Gateway Logs**: Request/response logging (can be enabled)
- **Amazon Cognito Logs**: Authentication events tracked

### Viewing Logs
```bash
# Lambda function logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/$STACK_NAME"

# Get recent logs
aws logs filter-log-events \
  --log-group-name "/aws/lambda/$STACK_NAME-mcp-server" \
  --start-time $(date -d '1 hour ago' +%s)000
```

## Troubleshooting

### Common Issues

1. **Package size exceeds 50MB**: Optimize dependencies or use Lambda layers
2. **Stack deployment fails**: Check CloudFormation events in AWS Console
3. **Authentication errors**: Verify Cognito user exists and password is set
4. **CORS errors**: Ensure OPTIONS method is properly configured

### Debug Commands

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION

# Test Lambda function directly
aws lambda invoke \
  --function-name $LAMBDA_FUNCTION_NAME \
  --payload '{"httpMethod":"GET","path":"/"}' \
  --region $REGION \
  response.json

# List Cognito users
aws cognito-idp list-users --user-pool-id $USER_POOL_ID --region $REGION
```

## Cleanup

To remove all deployed resources:

```bash
cd infrastructure
./cleanup.sh
```

This will delete:
- CloudFormation stack (Lambda, API Gateway, Cognito User Pool with all users, IAM roles)
- S3 deployment bucket (if auto-created)

After cleanup, you can redeploy from a clean state by running `./deploy.sh` again.

## Cost Optimization

- **Lambda**: Pay per request and execution time
- **API Gateway**: Pay per API call
- **Cognito**: Free tier includes 50,000 MAUs
- **CloudWatch**: Basic monitoring included

Estimated monthly cost for light usage (1000 requests): < $1 USD

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Verify AWS permissions and quotas
3. Review CloudFormation events for deployment issues
4. Test authentication flow with AWS CLI commands
