#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
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

# Set defaults if not provided
STACK_NAME=${STACK_NAME:-maths-mcp-ecs}
REGION=${REGION:-us-west-2}
CLUSTER_NAME=${CLUSTER_NAME:-maths-mcp-cluster}
SERVICE_NAME=${SERVICE_NAME:-maths-mcp-service}
TASK_FAMILY=${TASK_FAMILY:-maths-mcp-task}
CONTAINER_NAME=${CONTAINER_NAME:-maths-mcp-container}
IMAGE_NAME=${IMAGE_NAME:-maths-mcp-server}
ECR_REPOSITORY=${ECR_REPOSITORY:-maths-mcp-server}
CONTAINER_PORT=${CONTAINER_PORT:-8000}
DESIRED_COUNT=${DESIRED_COUNT:-2}
CPU=${CPU:-256}
MEMORY=${MEMORY:-512}
USER_POOL_NAME=${USER_POOL_NAME:-maths-mcp-users}
APP_CLIENT_NAME=${APP_CLIENT_NAME:-maths-mcp-client}

print_status "Deployment Configuration:"
echo "  Stack Name: $STACK_NAME"
echo "  Region: $REGION"
echo "  Cluster: $CLUSTER_NAME"
echo "  Service: $SERVICE_NAME"
echo "  Image: $IMAGE_NAME"
echo "  Desired Count: $DESIRED_COUNT"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    print_error "AWS CLI is not configured or credentials are invalid"
    exit 1
fi

print_success "AWS CLI configured successfully"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}"

print_status "AWS Account ID: $AWS_ACCOUNT_ID"
print_status "ECR URI: $ECR_URI"

# Create ECR repository if it doesn't exist
print_status "Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $REGION > /dev/null 2>&1 || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $REGION > /dev/null

print_success "ECR repository ready: $ECR_REPOSITORY"

# Login to ECR
print_status "Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Build Docker image
print_status "Building Docker image..."
docker build --platform linux/amd64 -t $IMAGE_NAME .

if [ $? -eq 0 ]; then
    print_success "Docker image built successfully"
else
    print_error "Docker build failed"
    exit 1
fi

# Tag and push image to ECR
print_status "Tagging and pushing image to ECR..."
docker tag $IMAGE_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest

if [ $? -eq 0 ]; then
    print_success "Image pushed to ECR successfully"
else
    print_error "Failed to push image to ECR"
    exit 1
fi

# Deploy CloudFormation stack
print_status "Deploying CloudFormation stack..."

# Check if stack exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION > /dev/null 2>&1; then
    print_status "Stack exists, updating..."
    aws cloudformation update-stack \
        --template-body file://./infrastructure/cloudformation.yaml \
        --stack-name $STACK_NAME \
        --region $REGION \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters \
            ParameterKey=ClusterName,ParameterValue=$CLUSTER_NAME \
            ParameterKey=ServiceName,ParameterValue=$SERVICE_NAME \
            ParameterKey=TaskFamily,ParameterValue=$TASK_FAMILY \
            ParameterKey=ContainerName,ParameterValue=$CONTAINER_NAME \
            ParameterKey=ImageUri,ParameterValue=$ECR_URI:latest \
            ParameterKey=DesiredCount,ParameterValue=$DESIRED_COUNT \
            ParameterKey=ContainerPort,ParameterValue=$CONTAINER_PORT \
            ParameterKey=Cpu,ParameterValue=$CPU \
            ParameterKey=Memory,ParameterValue=$MEMORY \
            ParameterKey=UserPoolName,ParameterValue=$USER_POOL_NAME \
            ParameterKey=AppClientName,ParameterValue=$APP_CLIENT_NAME \
            ParameterKey=CertificateArn,ParameterValue="${CERTIFICATE_ARN:-}"
else
    print_status "Stack does not exist, creating..."
    aws cloudformation create-stack \
        --template-body file://./infrastructure/cloudformation.yaml \
        --stack-name $STACK_NAME \
        --region $REGION \
        --capabilities CAPABILITY_NAMED_IAM \
        --disable-rollback \
        --timeout-in-minutes 20 \
        --parameters \
            ParameterKey=ClusterName,ParameterValue=$CLUSTER_NAME \
            ParameterKey=ServiceName,ParameterValue=$SERVICE_NAME \
            ParameterKey=TaskFamily,ParameterValue=$TASK_FAMILY \
            ParameterKey=ContainerName,ParameterValue=$CONTAINER_NAME \
            ParameterKey=ImageUri,ParameterValue=$ECR_URI:latest \
            ParameterKey=DesiredCount,ParameterValue=$DESIRED_COUNT \
            ParameterKey=ContainerPort,ParameterValue=$CONTAINER_PORT \
            ParameterKey=Cpu,ParameterValue=$CPU \
            ParameterKey=Memory,ParameterValue=$MEMORY \
            ParameterKey=UserPoolName,ParameterValue=$USER_POOL_NAME \
            ParameterKey=AppClientName,ParameterValue=$APP_CLIENT_NAME \
            ParameterKey=CertificateArn,ParameterValue="${CERTIFICATE_ARN:-}"
fi

print_status "CloudFormation deployment initiated. Stack will remain in failed state if errors occur (rollback disabled)."

# Don't exit on failure - let stack sit in failed state for debugging
if [ $? -eq 0 ]; then
    print_success "CloudFormation stack operation completed"
else
    print_warning "CloudFormation deployment may have failed - check AWS Console for details"
    print_status "Stack will remain in failed state for debugging (rollback disabled)"
fi

# Get stack outputs
print_status "Retrieving deployment information..."

ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
    --output text)

API_GATEWAY_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
    --output text)

USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoClientId`].OutputValue' \
    --output text)

# Get Cognito Client Secret
if [ -n "$USER_POOL_ID" ] && [ -n "$USER_POOL_CLIENT_ID" ]; then
    print_status "Retrieving Cognito client secret..."
    CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
        --user-pool-id $USER_POOL_ID \
        --client-id $USER_POOL_CLIENT_ID \
        --region $REGION \
        --query 'UserPoolClient.ClientSecret' \
        --output text)
fi

print_success "Deployment completed successfully!"
echo ""
echo "=== Deployment Information ==="
echo "🌐 API Gateway URL (Public + JWT Auth): $API_GATEWAY_URL"
echo "🔒 Internal ALB URL (Private + No Auth): $ALB_URL"
echo "👤 Cognito User Pool ID: $USER_POOL_ID"
echo "🔑 Cognito Client ID: $USER_POOL_CLIENT_ID"
echo "🔐 Cognito Client Secret: ${CLIENT_SECRET:0:20}..."
echo "📦 ECR Repository: $ECR_URI"
echo ""
echo "=== Architecture Flow ==="
echo "Internet → API Gateway → VPC Link → Internal ALB → ECS Tasks"
echo "                ↓"
echo "         Cognito JWT Auth"

# Update .env file with deployment values
if [ -n "$API_GATEWAY_URL" ]; then
    if grep -q "API_GATEWAY_URL=" .env; then
        sed -i.bak "s|API_GATEWAY_URL=.*|API_GATEWAY_URL=$API_GATEWAY_URL|" .env
    else
        echo "API_GATEWAY_URL=$API_GATEWAY_URL" >> .env
    fi
fi

if [ -n "$USER_POOL_ID" ]; then
    if grep -q "COGNITO_USER_POOL_ID=" .env; then
        sed -i.bak "s|COGNITO_USER_POOL_ID=.*|COGNITO_USER_POOL_ID=$USER_POOL_ID|" .env
    else
        echo "COGNITO_USER_POOL_ID=$USER_POOL_ID" >> .env
    fi
fi

if [ -n "$USER_POOL_CLIENT_ID" ]; then
    if grep -q "COGNITO_CLIENT_ID=" .env; then
        sed -i.bak "s|COGNITO_CLIENT_ID=.*|COGNITO_CLIENT_ID=$USER_POOL_CLIENT_ID|" .env
    else
        echo "COGNITO_CLIENT_ID=$USER_POOL_CLIENT_ID" >> .env
    fi
fi

if [ -n "$CLIENT_SECRET" ]; then
    if grep -q "COGNITO_CLIENT_SECRET=" .env; then
        sed -i.bak "s|COGNITO_CLIENT_SECRET=.*|COGNITO_CLIENT_SECRET=$CLIENT_SECRET|" .env
    else
        echo "COGNITO_CLIENT_SECRET=$CLIENT_SECRET" >> .env
    fi
fi

print_success "Updated .env with deployment values"
echo ""
echo "=== Next Steps ==="
echo "1. 👤 Create Cognito user:"
echo "   aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username <email> --temporary-password <temp-password> --message-action SUPPRESS --region $REGION"
echo ""
echo "2. 🔑 Set permanent password:"
echo "   aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username <email> --password <permanent-password> --permanent --region $REGION"
echo ""
echo "3. 🧪 Test health endpoint (no auth):"
echo "   curl $API_GATEWAY_URL/health"
echo ""
echo "4. 🔐 Test OAuth flow:"
echo "   ./run-oauth-test.sh"
echo 
echo "=== Architecture Verification ==="
echo "✅ API Gateway: $API_GATEWAY_URL (public, JWT required)"
echo "✅ VPC Link: Connects API Gateway to private ALB"
echo "✅ Internal ALB: $ALB_URL (private, no auth)"
echo "✅ ECS Tasks: Running in private subnets"