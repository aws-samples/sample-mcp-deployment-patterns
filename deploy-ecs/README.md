# Amazon ECS MCP Server Deployment

[Amazon Elastic Container Service (ECS)](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html) deployment of [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server with [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) and [Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html) OAuth authentication.

## 🏗️ Architecture

```
Internet → Amazon API Gateway (HTTP API) → VPC Link → Internal ALB → ECS Fargate Tasks
                ↓
         Amazon Cognito User Pool (JWT Auth)
```

**Components:**
- **Amazon API Gateway HTTP API**: Public endpoint with Amazon Cognito JWT authentication
- **VPC Link**: Connects Amazon API Gateway to internal resources
- **Internal [Application Load Balancer (ALB)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)**: Routes traffic to ECS tasks (private subnets)
- **[AWS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)**: Containerized MCP server in private subnets
- **Amazon Cognito User Pool**: OAuth 2.0 authentication
- **[Amazon Virtual Private Cloud (VPC)](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)**: Private/public subnets with NAT Gateway for outbound internet access

## 📁 Project Structure

```
deploy-ecs/
├── infrastructure/
│   ├── cloudformation.yaml    # Complete AWS infrastructure
│   ├── deploy.sh             # Deployment script
│   └── .env                  # Infrastructure configuration
├── src/
│   ├── mcp_server.py         # MCP server implementation
│   ├── ecs_server.py         # ECS-specific server wrapper
│   └── requirements.txt      # Python dependencies
├── .env                      # Main configuration
├── Dockerfile               # Container image definition
└── test-oauth-flow.py       # Full OAuth flow testing (browser-based)
```

## 🚀 Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
# Add COGNITO_USERNAME and COGNITO_PASSWORD for automatic user creation
```

### 2. Deploy Infrastructure
```bash
# From deploy-ecs folder
bash infrastructure/deploy.sh
```
- This will automatically:
-  Deploy CloudFormation stack
- Create Cognito user (if credentials provided in .env)
- Update .env with deployment values


### 3. Test Deployment
```bash
# Full OAuth flow (browser-based login)
python3 test-oauth-flow.py
```

## 🧪 Testing

### Complete OAuth Flow (Full Browser-Based Authentication)
```bash
python3 test-oauth-flow.py
```
- Opens browser for Cognito login
- Handles OAuth callback automatically
- Exchanges authorization code for JWT tokens
- Tests API Gateway with JWT token
- **Use this for full end-to-end OAuth testing**

## 🔧 Configuration

Key environment variables in `.env`:

**Required (auto-configured by deploy script):**
- `API_GATEWAY_URL`: API Gateway endpoint
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Cognito App Client ID
- `COGNITO_CLIENT_SECRET`: Cognito Client Secret

**Optional (for automatic user creation):**
- `COGNITO_USERNAME`: Email for test user (e.g., user@example.com)
- `COGNITO_PASSWORD`: Password for test user (min 8 chars, uppercase, lowercase, number)

**Note:** If `COGNITO_USERNAME` and `COGNITO_PASSWORD` are provided in `.env`, the deployment script will automatically create the user in Cognito User Pool.

## 🌐 VPC Link Architecture

**Why VPC Link?**
- **Security**: ECS tasks run in private subnets (no direct internet access)
- **Scalability**: API Gateway handles public traffic, authentication, and rate limiting
- **Cost**: No need for public load balancer or NAT Gateway for inbound traffic
- **Compliance**: Internal resources remain private while providing public API

**Traffic Flow:**
1. **Client** makes request to API Gateway public endpoint
2. **API Gateway** validates JWT token with Cognito
3. **VPC Link** securely forwards authenticated requests to private VPC
4. **Internal ALB** distributes traffic across ECS tasks in private subnets
5. **ECS Tasks** process MCP requests and return responses

## 📊 API Endpoints

### API Gateway (Public - Secure Routes Only)
- **Base URL**: `https://{api-id}.execute-api.{region}.amazonaws.com`
- **Health**: `GET /health` (no auth required)
- **MCP**: `POST /mcp` (requires JWT token in Authorization header)
- **OAuth**: `GET /authorize` (redirects to Cognito login)

### Internal ALB (Private - No Auth)
- **Base URL**: `http://{alb-dns}.{region}.elb.amazonaws.com`
- **Health**: `GET /health`
- **MCP**: `POST /mcp` (direct access, no authentication)

**Security**: Only explicit routes are accessible - no catch-all proxy routes
**Traffic Flow**: API Gateway → VPC Link → Internal ALB → ECS Tasks

## 🔐 Authentication Flow

### OAuth 2.0 Flow
1. **Authorization Request**: Client redirects to Cognito authorization URL
2. **User Login**: User authenticates with Cognito User Pool
3. **Authorization Code**: Cognito returns authorization code to callback URL
4. **Token Exchange**: Client exchanges code + client secret for JWT tokens
5. **API Access**: Use ID token in `Authorization: Bearer <token>` header

### Network Flow
```
Client → API Gateway → JWT Authorizer (validates Cognito token)
                    ↓ (if valid)
              VPC Link → Internal ALB → ECS Tasks
```

**Security**: API Gateway validates JWT tokens before forwarding to internal resources

## 🛠️ Development

### Automated Configuration
The deploy script automatically:
- Deploys CloudFormation stack
- Retrieves Cognito client secret
- Updates `.env` with all deployment values
- **Creates Cognito user if `COGNITO_USERNAME` and `COGNITO_PASSWORD` are provided in `.env`**
- No manual configuration required

### Manual Testing

#### API Gateway (Public + JWT Auth)
```bash
# Test health endpoint (no auth)
source .env && curl $API_GATEWAY_URL/health

# Test complete OAuth flow (gets JWT token automatically)
python3 test-oauth-flow.py
```

#### Internal ALB (Private + No Auth)
```bash
# Direct access from within VPC (no authentication)
source .env && curl $ALB_URL/health
source .env && curl -X POST $ALB_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Redeploy After Changes
```bash
# From deploy-ecs folder
bash infrastructure/deploy.sh
```

## 📋 Available MCP Tools

- `add_numbers`: Add two numbers
- `multiply_numbers`: Multiply two numbers  
- `divide_numbers`: Divide two numbers
- `power_numbers`: Raise to power
- `greet_user`: Greet user by name