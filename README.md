# MCP Maths Server - Multiple Deployment Methods

A Mathematics [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server demonstrating different deployment approaches on AWS with comprehensive authentication options.

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Configuration Management](#configuration-management)
- [Deployment Methods](#deployment-methods)
  - [AgentCore with SigV4/IAM Auth](#1-amazon-bedrock-agentcore-with-sigv4iam-authentication)
  - [AgentCore with OAuth Auth](#2-amazon-bedrock-agentcore-with-oauthcognito-authentication)
  - [Serverless Lambda](#3-serverless-aws-lambda--amazon-api-gateway)
  - [ECS Container Deployment](#4-amazon-ecs-container-deployment)
  - [EKS Kubernetes Deployment](#5-amazon-eks-kubernetes-deployment)
- [Testing with MCP Inspector](#testing-with-mcp-inspector)
- [Comparison Table](#comparison-of-deployment-methods)
- [Troubleshooting](#troubleshooting)

---

## Overview

This project demonstrates different AWS deployment patterns for MCP servers:

1. **[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/) with [SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html)/IAM** - Production-ready with [AWS Identity and Access Management (IAM)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) authentication
2. **Amazon Bedrock AgentCore with OAuth** - User-based authentication with [Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html) JWT tokens
3. **Serverless [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)** - Cost-effective auto-scaling deployment
4. **[Amazon Elastic Container Service (ECS)](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html) Container** - Containerized deployment with Application Load Balancer
5. **[Amazon Elastic Kubernetes Service (EKS)](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html) Kubernetes** - Kubernetes deployment with [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) and SigV4 authentication

**Key Features:**
- ✅ No hardcoded credentials - all configuration via `.env` files
- ✅ Multiple authentication methods (IAM, OAuth, Cognito)
- ✅ Easy testing with MCP Inspector
- ✅ Production-ready deployment scripts
- ✅ Comprehensive documentation

---

## Project Structure

```
maths/
├── deploy-agentcore-iam/          # AgentCore deployment with SigV4/IAM auth
│   ├── .env                   # Configuration (gitignored)
│   ├── .env.example           # Template for configuration
│   ├── infrastructure/        # Deployment scripts
│   └── src/                   # MCP server implementation
├── deploy-agentcore-oauth/    # AgentCore deployment with OAuth
│   ├── .env                   # Configuration (gitignored)
│   ├── .env.example           # Template for configuration
│   ├── infrastructure/        # Deployment scripts with OAuth config
│   ├── get-access-token.py    # Script to get Cognito access tokens
│   └── src/                   # MCP server implementation
├── deploy-ecs/                # ECS container deployment
│   ├── .env                   # Configuration (gitignored)
│   ├── .env.example           # Template for configuration
│   ├── infrastructure/        # CloudFormation templates
│   └── src/                   # MCP server implementation
├── deploy-eks/                # EKS Kubernetes deployment
│   ├── deployment/            # 3-step deployment scripts
│   ├── infrastructure/        # CloudFormation templates
│   ├── k8s/                   # Kubernetes manifests
│   └── src/                   # MCP server implementation
├── deploy-serverless/         # Serverless Lambda deployment
│   ├── .env                   # Configuration (gitignored)
│   ├── .env.example           # Template for configuration
│   ├── infrastructure/        # CloudFormation + deployment scripts
│   └── src/                   # Lambda function + MCP server
└── mcp-inspector/             # Testing tools for all deployments
    ├── agentcore-proxy-sigv4.py       # Test AgentCore with SigV4
    ├── agentcore-proxy-oauth.py       # Test AgentCore with OAuth
    └── serverless-proxy.py            # Test Serverless deployment
```

---

## Configuration Management

**All deployments use `.env` files - NO hardcoded credentials.**

### Setting Up Configuration

Each deployment folder has `.env.example` templates:

```bash
# For AgentCore with SigV4/IAM
cd deploy-agentcore
cp .env.example .env
# Edit .env with your configuration

# For AgentCore with OAuth
cd deploy-agentcore-oauth
cp .env.example .env
# Edit .env with your configuration

# For Serverless
cd deploy-serverless
cp .env.example .env
# Edit .env with your configuration
```

---

## Deployment Methods

### 1. Amazon Bedrock AgentCore with SigV4/IAM Authentication

**Use Case:** Production deployments with AWS IAM authentication

**Configuration** (`deploy-agentcore-iam/.env`):
```bash
# AgentCore Configuration
AGENT_NAME=maths_mcp_agentcore
REGION=ap-southeast-2
AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:region:account:runtime/agent-name

# Amazon Cognito Configuration (optional, for token generation)
COGNITO_USER_POOL_ID=your-region_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret
COGNITO_REGION=your-region
COGNITO_USERNAME=your-email@example.com
COGNITO_PASSWORD=YourSecurePassword123!
```

**Deploy:**
```bash
cd deploy-agentcore-iam/infrastructure
./deploy.sh
```

**What happens:**
- Loads configuration from `.env`
- Uses AWS IAM credentials ([SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) signing)
- No JWT tokens needed
- Deploys to Amazon Bedrock AgentCore

**Test with MCP Inspector:**
```bash
cd mcp-inspector
npx @modelcontextprotocol/inspector python3 agentcore-proxy-sigv4.py
```
---

### 2. Amazon Bedrock AgentCore with OAuth/Cognito Authentication

**Use Case:** User-based authentication with JWT tokens

**Configuration** (`deploy-agentcore-oauth/.env`):
```bash
# AgentCore Configuration
AGENT_NAME=maths_mcp_agentcore_oauth
REGION=ap-southeast-2

# OAuth Configuration
OAUTH_DISCOVERY_URL=https://cognito-idp.region.amazonaws.com/pool-id/.well-known/openid-configuration
OAUTH_CLIENT_ID=your-client-id

# Amazon Cognito Configuration
COGNITO_USER_POOL_ID=your-region_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret
COGNITO_REGION=your-region
COGNITO_USERNAME=your-email@example.com
COGNITO_PASSWORD=YourSecurePassword123!
```

**Deploy:**
```bash
cd deploy-agentcore-oauth/infrastructure
./deploy.sh
```

**What happens:**
- Loads `OAUTH_DISCOVERY_URL` and `OAUTH_CLIENT_ID` from `.env` (lines 30-36 in deploy.sh)
- Configures Amazon Bedrock AgentCore with OAuth authentication
- Requires JWT tokens for access
- [AWS AgentCore OAuth docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html):
- `client_id`: Must match one of the `allowedClients` (REQUIRED)
- `aud`: Must match `allowedAudience` IF SPECIFIED (OPTIONAL)

**By removing `allowedAudience`, Amazon Cognito ACCESS tokens (which have `client_id` but not `aud`) work correctly!**

**Get Access Token:**
```bash
cd deploy-agentcore-oauth
python3 get-access-token.py
# Copy the ACCESS TOKEN from output
```

**Test with MCP Inspector:**
```bash
cd mcp-inspector
export BEARER_TOKEN="your-access-token-here"
npx @modelcontextprotocol/inspector python3 agentcore-proxy-oauth.py

or 

npx @modelcontextprotocol/inspector ./02-start-oauth-proxy.sh agentcore-proxy-oauth.py

```
---





### 3. Serverless (AWS Lambda + Amazon API Gateway)

**Configuration** (`deploy-serverless/.env`):
```bash
# Deployment Configuration
STACK_NAME=maths-mcp-server
REGION=ap-southeast-2
STAGE=dev
USER_POOL_NAME=maths-mcp-users
APP_CLIENT_NAME=maths-mcp-client

# Amazon Cognito User Credentials for Testing
COGNITO_USERNAME=your-email@example.com
COGNITO_PASSWORD=YourSecurePassword123!

# Amazon Cognito Configuration (from AWS CloudFormation outputs)
COGNITO_USER_POOL_ID=your-region_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id
COGNITO_REGION=your-region
```

**Deploy:**
```bash
cd deploy-serverless/infrastructure
./deploy.sh
```

**What happens:**
- Loads all configuration from `.env` (lines 29-36 in deploy.sh)
- Uses [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) to create infrastructure
- Creates Amazon Cognito User Pool with the configured names
- Deploys AWS Lambda function with Amazon API Gateway

**Test with MCP Inspector:**
```bash
cd mcp-inspector
./start-serverless-proxy.sh

or 

npx @modelcontextprotocol/inspector ./03-start-lambda-proxy.sh agentcore-lambda-proxy.py

```

---

### 4. Amazon ECS Container Deployment

**Use Case:** Containerized deployment with [Application Load Balancer (ALB)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)

**Configuration** (`deploy-ecs/.env`):
```bash
# Amazon ECS Configuration
CLUSTER_NAME=maths-mcp-ecs
SERVICE_NAME=maths-mcp-service
TASK_FAMILY=maths-mcp-task
REGION=us-west-2

# Container Configuration
IMAGE_NAME=maths-mcp-server
ECR_REPOSITORY=maths-mcp-server
CONTAINER_PORT=8000

# Load Balancer Configuration
ALB_NAME=maths-mcp-alb
TARGET_GROUP_NAME=maths-mcp-targets
```

**Deploy:**
```bash
cd deploy-ecs/infrastructure
./deploy.sh
```

**What happens:**
- Creates Amazon ECS cluster with [AWS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) tasks
- Builds and pushes Docker image to [Amazon Elastic Container Registry (ECR)](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)
- Sets up Application Load Balancer
- Configures auto-scaling and health checks

**Test:**
```bash
# Health check
curl http://YOUR_ALB_URL/health

# MCP endpoint
curl -X POST http://YOUR_ALB_URL/mcp \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/list","id":1}'
```

---

### 5. Amazon EKS Kubernetes Deployment

**Use Case:** Production Kubernetes deployment with Amazon API Gateway and [SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) authentication

**Architecture:**
```
Internet → Amazon API Gateway (SigV4) → VPC Link → Internal ALB → EKS Pods (MCP Server)
```

**Configuration** (`deploy-eks/.env`):
```bash
# Amazon EKS Configuration
CLUSTER_NAME=maths-mcp-eks
REGION=us-west-2
NAMESPACE=mcp-server

# Container Configuration
IMAGE_NAME=maths-mcp-server
ECR_REPOSITORY=maths-mcp-server
REPLICAS=2

# Auto-configured by deployment scripts
VPC_ID=
ECR_URI=
INTERNAL_ALB_URL=
API_GATEWAY_URL=
```

**Deploy (3-Step Process):**
```bash
cd deploy-eks/deployment

# Step 1: Deploy EKS infrastructure
./01-deploy-infrastructure.sh

# Step 2: Deploy MCP server workload
./02-deploy-workload.sh

# Step 3: Deploy API Gateway with authentication
./03-deploy-api-gateway.sh
```

**What happens:**
- **Step 1**: Creates Amazon EKS cluster, [Amazon Virtual Private Cloud (VPC)](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html), and AWS Load Balancer Controller
- **Step 2**: Builds Docker image, deploys to Kubernetes with internal ALB
- **Step 3**: Creates Amazon API Gateway with VPC Link and SigV4 authentication

**Test:**
```bash
# Health endpoint (no authentication)
curl https://YOUR_API_GATEWAY_URL/health

# MCP endpoints (SigV4 authentication required)
cd deploy-eks/deployment
python3 test-api.py
```

**Security Features:**
- ✅ Internal ALB only (no direct public access)
- ✅ Amazon API Gateway with [SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) authentication for MCP endpoints
- ✅ Health endpoint accessible for monitoring
- ✅ VPC Link for secure private connectivity
- ✅ IAM policies for fine-grained access control

**Cleanup:**
```bash
cd deploy-eks/deployment
./cleanup.sh
```

---

## Testing with MCP Inspector

All three deployments can be tested using MCP Inspector.

### Prerequisites
```bash
npm install -g @modelcontextprotocol/inspector
pip install mcp httpx boto3 python-dotenv botocore
```

### Testing Commands

| Deployment | Command | Auth Method | Token Needed |
|------------|---------|-------------|--------------|
| **AgentCore [SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html)** | `npx @modelcontextprotocol/inspector python3 agentcore-proxy-sigv4.py` | AWS IAM | No |
| **AgentCore OAuth** | `npx @modelcontextprotocol/inspector ./02-start-oauth-proxy.sh agentcore-proxy-oauth.py` | Amazon Cognito JWT | Access Token |
| **ECS Container** | `curl http://ALB_URL/health` | None | No |
| **EKS Kubernetes** | `cd mcp-inspector && ./05-start-eks-proxy.sh` | AWS SigV4 | No |
| **Serverless** | `npx @modelcontextprotocol/inspector ./03-start-lambda-proxy.sh` | Amazon Cognito | ID Token |


## Comparison of Deployment Methods

| Feature | AgentCore (SigV4) | AgentCore (OAuth) | ECS Container | EKS Kubernetes | Serverless (Lambda) |
|---------|-------------------|-------------------|---------------|----------------|---------------------|
| **Authentication** | [AWS IAM (SigV4)](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) | Amazon Cognito JWT | None (ALB) | SigV4 + Public Health | Amazon Cognito User Pool |
| **Configuration** | `.env` file | `.env` file | `.env` file | `.env` file | `.env` file |
| **Setup Complexity** | Medium | Medium-High | Medium | High | High |
| **Cost Model** | Pay per runtime hour | Pay per runtime hour | Pay for running containers | Pay for EKS + EC2 instances | Pay per request |
| **Cold Start** | No | No | No | No | Yes (~500ms) |
| **Scalability** | Manual | Manual | Auto-scaling | Kubernetes HPA | Automatic |
| **Security** | IAM-based | JWT-based | Network-based | Amazon API Gateway + IAM | Amazon API Gateway + Cognito |
| **Best For** | Production with IAM | User-based apps | Simple containerized apps | Enterprise Kubernetes | Cost-sensitive, variable load |
| **Infrastructure** | Managed service | Managed service | ECS + ALB | EKS + ALB + API Gateway | Lambda + API Gateway |

---

## Development Workflow

### Making Changes to the MCP Server

1. Edit server code in `src/` folder of the relevant deployment
2. Redeploy:
   ```bash
   cd <deployment-folder>/infrastructure
   ./deploy.sh
   ```
3. Test with MCP Inspector using the appropriate proxy script

### Testing Different Authentication Methods

1. **SigV4/IAM** - Best for testing with your AWS credentials
2. **OAuth** - Best for testing user-based authentication flows
3. **Serverless** - Best for testing API Gateway integration

---

## Additional Resources

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/)
- [MCP Inspector Documentation](https://github.com/modelcontextprotocol/inspector)
- [Amazon Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [AWS Signature Version 4 (SigV4)](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html)
- [AWS Identity and Access Management (IAM)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html)

---

## Troubleshooting

### Amazon Bedrock AgentCore Deployment Issues

**Error: Agent not found**
```bash
# Check agent status
cd deploy-agentcore-iam/infrastructure
agentcore status --agent maths_mcp_agentcore
```

**Error: Invalid OAuth token**
```bash
# Get fresh access token
cd deploy-agentcore-oauth
python3 get-access-token.py
```

**Error: .env file not found**
```bash
# Copy template and configure
cp .env.example .env
# Edit .env with your values
```

### Amazon ECS Deployment Issues

**Error: Task failed to start**
```bash
# Check ECS task logs
aws ecs describe-tasks --cluster CLUSTER_NAME --tasks TASK_ARN
aws logs get-log-events --log-group-name /ecs/maths-mcp-task
```

**Error: ALB health check failing**
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN
```

**Error: ECR push failed**
```bash
# Login to Amazon ECR
aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com
```

### Amazon EKS Deployment Issues

**Error: Cluster not found**
```bash
# Check cluster status
aws eks describe-cluster --name CLUSTER_NAME --region REGION
```

**Error: Pods not starting**
```bash
# Check pod status and logs
kubectl get pods -n mcp-server
kubectl logs -f deployment/maths-mcp-server -n mcp-server
```

**Error: ALB not created**
```bash
# Check ingress status
kubectl describe ingress maths-mcp-server-internal -n mcp-server
```

**Error: Amazon API Gateway 403 Forbidden**
```bash
# Attach IAM policy to your user/role
aws iam attach-user-policy --user-name USERNAME --policy-arn POLICY_ARN
```

### Serverless Deployment Issues

**Error: Stack already exists**
```bash
# Script handles updates automatically
cd deploy-serverless/infrastructure
./deploy.sh
```

**Error: Lambda package too large**
```bash
# Check package size (should be < 50MB)
cd deploy-serverless/infrastructure
du -sm build/
```

### MCP Inspector Issues

**Error: Connection refused**
- Ensure deployment is complete and agent is READY
- Check `.env` file has correct `AGENT_RUNTIME_ARN`
- Verify AWS credentials are configured

**Error: Token expired (OAuth)**
```bash
# Get new access token
cd deploy-agentcore-oauth
python3 get-access-token.py
```

**Error: Module not found**
```bash
# Install dependencies
pip install mcp httpx boto3 python-dotenv botocore
```

---

## Contributing

When adding new features:
1. Update all deployment methods to maintain parity
2. Add corresponding tests in mcp-inspector
3. Update this README with new configuration requirements
4. Update `.env.example` templates

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

