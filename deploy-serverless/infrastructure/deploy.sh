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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    print_status "Loading environment variables from .env file..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    print_error ".env file not found at $ENV_FILE"
    print_error "Please create one with required variables."
    exit 1
fi

# Set defaults if not provided
STACK_NAME=${STACK_NAME:-maths-mcp-server}
REGION=${REGION:-us-east-1}
STAGE=${STAGE:-dev}
USER_POOL_NAME=${USER_POOL_NAME:-maths-mcp-users}
APP_CLIENT_NAME=${APP_CLIENT_NAME:-maths-mcp-client}

print_status "Deployment Configuration:"
echo "  Stack Name: $STACK_NAME"
echo "  Region: $REGION"
echo "  Stage: $STAGE"
echo "  User Pool: $USER_POOL_NAME"
echo "  App Client: $APP_CLIENT_NAME"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    print_error "AWS CLI is not configured or credentials are invalid"
    exit 1
fi

print_success "AWS CLI configured successfully"

# Create S3 bucket for deployment artifacts if not specified
if [ -z "$S3_BUCKET" ]; then
    S3_BUCKET="${STACK_NAME}-deployment-$(date +%s)"
    print_status "Creating S3 bucket: $S3_BUCKET"
    
    if [ "$REGION" = "us-east-1" ]; then
        aws s3 mb s3://$S3_BUCKET --region $REGION
    else
        aws s3api create-bucket --bucket $S3_BUCKET --region $REGION --create-bucket-configuration LocationConstraint=$REGION
    fi
    
    print_success "S3 bucket created: $S3_BUCKET"
else
    print_status "Using existing S3 bucket: $S3_BUCKET"
fi

# Create deployment package
print_status "Creating Lambda deployment package..."

# Clean up previous builds
rm -rf "$SCRIPT_DIR/build/"
mkdir -p "$SCRIPT_DIR/build/"

# Copy source files
cp "$SCRIPT_DIR/../src/lambda_function.py" "$SCRIPT_DIR/build/"
cp "$SCRIPT_DIR/../src/mcp_server.py" "$SCRIPT_DIR/build/"

# Install dependencies
print_status "Installing Python dependencies..."
pip3 install -r "$SCRIPT_DIR/../src/requirements.txt" -t "$SCRIPT_DIR/build/" --quiet

# Check package size
PACKAGE_SIZE=$(du -sm "$SCRIPT_DIR/build/" | cut -f1)
print_status "Package size: ${PACKAGE_SIZE}MB"

if [ $PACKAGE_SIZE -gt 50 ]; then
    print_error "Package size exceeds 50MB Lambda limit"
    exit 1
fi

# Create ZIP file
cd "$SCRIPT_DIR/build/"
zip -r "$SCRIPT_DIR/deployment-package.zip" . > /dev/null
cd "$SCRIPT_DIR"

print_success "Deployment package created: deployment-package.zip"

# Deploy CloudFormation stack
print_status "Deploying CloudFormation stack..."

aws cloudformation deploy \
    --template-file "$SCRIPT_DIR/cloudformation.yaml" \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        DeploymentStage=$STAGE \
        UserPoolName=$USER_POOL_NAME \
        AppClientName=$APP_CLIENT_NAME

if [ $? -eq 0 ]; then
    print_success "CloudFormation stack deployed successfully"
else
    print_error "CloudFormation deployment failed"
    exit 1
fi

# Get Lambda function name from stack outputs
LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
    --output text)

if [ -z "$LAMBDA_FUNCTION_NAME" ]; then
    print_error "Could not retrieve Lambda function name from stack outputs"
    exit 1
fi

print_status "Updating Lambda function code..."

# Update Lambda function with deployment package
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --zip-file "fileb://$SCRIPT_DIR/deployment-package.zip" \
    --region $REGION > /dev/null

print_success "Lambda function updated successfully"

# Get stack outputs
print_status "Retrieving deployment information..."

API_URL=$(aws cloudformation describe-stacks \
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
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolClientId`].OutputValue' \
    --output text)

# Clean up
rm -rf "$SCRIPT_DIR/build/"
rm "$SCRIPT_DIR/deployment-package.zip"

# Auto-create Cognito user if credentials provided
if [ -n "$COGNITO_USERNAME" ] && [ -n "$COGNITO_PASSWORD" ]; then
    print_status "Creating Cognito test user..."
    
    # Check if user already exists
    if aws cognito-idp admin-get-user --user-pool-id $USER_POOL_ID --username $COGNITO_USERNAME --region $REGION > /dev/null 2>&1; then
        print_status "User already exists: $COGNITO_USERNAME"
    else
        # Create user with permanent password
        aws cognito-idp admin-create-user \
            --user-pool-id $USER_POOL_ID \
            --username $COGNITO_USERNAME \
            --message-action SUPPRESS \
            --region $REGION > /dev/null
        
        aws cognito-idp admin-set-user-password \
            --user-pool-id $USER_POOL_ID \
            --username $COGNITO_USERNAME \
            --password $COGNITO_PASSWORD \
            --permanent \
            --region $REGION > /dev/null
        
        print_success "Test user created: $COGNITO_USERNAME"
    fi
fi

print_success "Deployment completed successfully!"
echo ""
echo "=== Deployment Information ==="
echo "API Gateway URL: $API_URL"
echo "MCP Endpoint: $API_URL/mcp"
echo "Health Check: $API_URL/"
echo "User Pool ID: $USER_POOL_ID"
echo "User Pool Client ID: $USER_POOL_CLIENT_ID"
echo "Lambda Function: $LAMBDA_FUNCTION_NAME"
echo ""
echo "=== Test the Deployment ==="
echo "Health check:"
echo "  curl $API_URL/"
echo ""
echo "MCP Inspector:"
echo "  cd ../mcp-inspector"
echo "  npx @modelcontextprotocol/inspector ./03-start-lambda-proxy.sh"
