# Amazon EKS MCP Server Deployment

A complete deployment solution for running a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server on [Amazon Elastic Kubernetes Service (EKS)](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html) with [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) and [SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) authentication.

## Architecture

```
Internet → Amazon API Gateway (SigV4) → VPC Link → Internal ALB → EKS Pods (MCP Server)
```

**Secure Design**: Only internal [Application Load Balancer (ALB)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html) is deployed in private subnets. All external access requires Amazon API Gateway with [SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) authentication.

## Features

- ✅ **Amazon EKS Cluster** with managed node groups
- ✅ **MCP Server** running in Kubernetes pods
- ✅ **Internal ALB** for secure private access only
- ✅ **Amazon API Gateway** with [AWS Signature Version 4 (SigV4)](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) authentication
- ✅ **VPC Link** for secure private connectivity
- ✅ **[AWS Identity and Access Management (IAM)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) Policies** for fine-grained access control
- ✅ **[Amazon Elastic Container Registry (ECR)](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html) Integration** for container image management

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Docker** installed and running
3. **kubectl** installed
4. **Python 3** with boto3 and requests-aws4auth packages
5. **AWS Account** with permissions for:
   - Amazon EKS, EC2, VPC, IAM, AWS CloudFormation
   - Amazon API Gateway, Amazon ECR, Application Load Balancer

## Quick Start

### 1. Configuration

Copy and configure the environment file:

```bash
cp .env.example .env
# Edit .env with your settings
```

Required variables in `.env`:
```bash
CLUSTER_NAME=maths-mcp-eks
REGION=us-west-2
NAMESPACE=mcp-server
IMAGE_NAME=maths-mcp-server
ECR_REPOSITORY=maths-mcp-server
REPLICAS=2
ACM_CERTIFICATE_ARN=arn:aws:acm:REGION:ACCOUNT_ID:certificate/CERTIFICATE_ID
INTERNAL_ALB_SERVER_NAME=mcp.internal.example.com
```

The certificate must cover `INTERNAL_ALB_SERVER_NAME`. API Gateway uses this
name for TLS verification when connecting through the VPC Link. If clients
inside the VPC need direct ALB access, create a private DNS alias from this name
to the AWS-generated ALB hostname printed by the workload deployment script.

### 2. Step-by-Step Deployment

Deploy each step individually:

```bash
cd deployment/

# Step 1: Deploy EKS infrastructure
./01-deploy-infrastructure.sh

# Step 2: Deploy MCP server workload
./02-deploy-workload.sh

# Step 3: Deploy API Gateway with authentication
./03-deploy-api-gateway.sh
```

## Deployment Steps Explained

### Step 1: Infrastructure (`01-deploy-infrastructure.sh`)

Deploys:
- [Amazon Virtual Private Cloud (VPC)](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html) with public subnets (for NAT Gateway) and private subnets (for workloads)
- Amazon EKS cluster with managed node groups
- AWS Load Balancer Controller
- [AWS Identity and Access Management (IAM)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) roles and policies

**Duration**: ~15-20 minutes

### Step 2: Workload (`02-deploy-workload.sh`)

Deploys:
- Builds and pushes Docker image to [Amazon Elastic Container Registry (ECR)](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)
- Creates Kubernetes namespace
- Deploys MCP server pods
- Creates services and ingress
- Sets up an HTTPS-only internal ALB (private access only)

**Duration**: ~10-15 minutes

### Step 3: API Gateway (`03-deploy-api-gateway.sh`)

Deploys:
- Amazon API Gateway with HTTP API
- VPC Link to internal ALB
- [SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) (IAM) authentication
- IAM policies for access control

**Duration**: ~5-10 minutes

## Testing Your Deployment

### Test API Gateway

**Health Endpoint (No Authentication):**
```bash
curl https://YOUR_API_GATEWAY_URL/health
```

**MCP Endpoints (SigV4 Authentication Required):**
```bash
cd deployment/
python3 test-api.py
```



## API Endpoints

### Health Check (No Authentication Required)
```bash
GET /health
```
Returns service status - accessible without authentication for monitoring purposes.

### MCP Protocol ([SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) Authentication Required)
```bash
POST /mcp
Content-Type: application/json

# List available tools
{"method":"tools/list","id":1}

# Call a tool
{"method":"tools/call","params":{"name":"add_numbers","arguments":{"a":5,"b":3}},"id":2}
```
All MCP operations require [AWS Signature Version 4 (SigV4)](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) authentication and proper IAM permissions.

## Available MCP Tools

- `add_numbers` - Add two numbers
- `multiply_numbers` - Multiply two numbers  
- `divide_numbers` - Divide two numbers
- `power_numbers` - Raise base to power
- `greet_user` - Greet a user by name

## Access Control

### Amazon API Gateway (Recommended)
- **URL**: `https://YOUR_API_ID.execute-api.REGION.amazonaws.com`
- **Authentication**: [AWS SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) (IAM)
- **Security**: Requires valid AWS credentials and IAM permissions

### Internal ALB (Not Directly Accessible)
- **Internal ALB**: Private network only (VPC isolation)
- **Access**: Only via Amazon API Gateway with SigV4 authentication
- **Security**: Network-level isolation in private subnets

## IAM Permissions

To access the Amazon API Gateway, attach the created IAM policy to your user/role:

```bash
# Get the policy ARN from deployment output
aws iam attach-user-policy --user-name YOUR_USERNAME --policy-arn POLICY_ARN
# or
aws iam attach-role-policy --role-name YOUR_ROLE --policy-arn POLICY_ARN
```

## Monitoring and Troubleshooting

### Check EKS Cluster
```bash
aws eks describe-cluster --name maths-mcp-eks --region us-west-2
kubectl get nodes
```

### Check Pods
```bash
kubectl get pods -n mcp-server
kubectl logs -f deployment/maths-mcp-server -n mcp-server
```

### Check Internal ALB
```bash
aws elbv2 describe-load-balancers --region us-west-2 --query "LoadBalancers[?Scheme=='internal']"
```

### Check API Gateway
```bash
aws apigatewayv2 get-apis --region us-west-2
```

## Cleanup

Remove all deployed resources:

```bash
cd deployment/
./cleanup.sh
```

**Warning**: This will delete everything including the EKS cluster, internal ALB, API Gateway, and ECR repository.

## Cost Optimization

- **EKS Cluster**: ~$0.10/hour for control plane
- **EC2 Instances**: Based on node group instance types
- **Internal ALB**: ~$0.0225/hour
- **API Gateway**: Pay per request
- **ECR**: Storage costs for Docker images

To minimize costs:
- Use smaller instance types for development
- Scale down node groups when not in use
- Delete resources when not needed

## Troubleshooting

### Common Issues

1. **"Cluster not found"**
   - Ensure Step 1 completed successfully
   - Check AWS region configuration

2. **"Cannot connect to EKS cluster"**
   - Update kubeconfig: `aws eks update-kubeconfig --region REGION --name CLUSTER_NAME`
   - Check AWS credentials

3. **"ALB not found"**
   - Ensure Step 2 completed successfully
   - Wait for ALB creation (can take 5-10 minutes)

4. **"403 Forbidden" on API Gateway**
   - Attach the IAM policy to your user/role
   - Check AWS credentials are properly configured

5. **Docker build fails**
   - Ensure Docker is running
   - Check Dockerfile and source code

### Getting Help

1. Check CloudFormation events for deployment issues
2. Check EKS cluster logs in CloudWatch
3. Check pod logs: `kubectl logs -f deployment/maths-mcp-server -n mcp-server`
4. Verify AWS permissions and quotas

## File Structure

```
deploy-eks/
├── deployment/                 # Deployment scripts
│   ├── 01-deploy-infrastructure.sh
│   ├── 02-deploy-workload.sh
│   ├── 03-deploy-api-gateway.sh
│   ├── cleanup.sh
│   └── test-api.py
├── infrastructure/             # CloudFormation templates
│   ├── cloudformation.yaml
│   └── api-gateway.yaml
├── k8s/                       # Kubernetes manifests
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── src/                       # MCP server source code
│   ├── mcp_server.py
│   ├── ecs_server.py
│   └── requirements.txt
├── .env                       # Environment configuration
├── .env.example              # Example configuration
├── Dockerfile                # Container definition
└── README.md                 # This file
```

## Security Best Practices

1. **Use Amazon API Gateway** for all external access (internal ALB is VPC-only)
2. **Enable [AWS CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html)** for API access logging
3. **Use least privilege** IAM policies
4. **Enable VPC Flow Logs** for network monitoring
5. **Regularly update** container images and dependencies
6. **Use [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)** for sensitive configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
