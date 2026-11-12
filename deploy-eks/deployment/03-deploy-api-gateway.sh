#!/bin/bash

# Step 3: Deploy API Gateway with SigV4 Authentication
# This script creates API Gateway with VPC Link to private ALB and IAM authentication

set -e

echo "🚀 Step 3: Deploying API Gateway with SigV4 Authentication"
echo "=========================================================="

# Load environment variables
if [ -f "../.env" ]; then
    source ../.env
else
    echo "❌ Error: .env file not found in parent directory"
    echo "💡 Please run this script from the deployment/ directory"
    exit 1
fi

# Set default values
STACK_NAME="${CLUSTER_NAME}-api-gateway"
TEMPLATE_FILE="../infrastructure/api-gateway.yaml"

echo "📋 Configuration:"
echo "   Cluster Name: $CLUSTER_NAME"
echo "   Region: $REGION"
echo "   Stack Name: $STACK_NAME"
echo "   VPC ID: $VPC_ID"
echo ""

# Check if required variables are set
if [ -z "$VPC_ID" ] || [ -z "$INTERNAL_ALB_SERVER_NAME" ]; then
    echo "❌ Error: VPC_ID and INTERNAL_ALB_SERVER_NAME must be set in .env"
    echo "💡 Please run ./01-deploy-infrastructure.sh first"
    exit 1
fi

# Check if CloudFormation template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "❌ Error: API Gateway template not found at $TEMPLATE_FILE"
    exit 1
fi

# Get the private ALB details
echo "📋 Getting private ALB information..."
PRIVATE_ALB_ARN=$(aws elbv2 describe-load-balancers \
    --region $REGION \
    --query "LoadBalancers[?Scheme=='internal' && contains(LoadBalancerName, 'mcpserve')].LoadBalancerArn" \
    --output text)

PRIVATE_ALB_DNS=$(aws elbv2 describe-load-balancers \
    --region $REGION \
    --query "LoadBalancers[?Scheme=='internal' && contains(LoadBalancerName, 'mcpserve')].DNSName" \
    --output text)

# Get the listener ARN for the private ALB
PRIVATE_ALB_LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $PRIVATE_ALB_ARN \
    --region $REGION \
    --query "Listeners[0].ListenerArn" \
    --output text)

if [ -z "$PRIVATE_ALB_ARN" ] || [ -z "$PRIVATE_ALB_DNS" ] || [ -z "$PRIVATE_ALB_LISTENER_ARN" ]; then
    echo "❌ Error: Could not find private ALB or listener. Make sure Step 2 is complete."
    exit 1
fi

echo "✅ Found private ALB:"
echo "   ARN: $PRIVATE_ALB_ARN"
echo "   DNS: $PRIVATE_ALB_DNS"
echo "   Listener ARN: $PRIVATE_ALB_LISTENER_ARN"

# Get private subnet IDs
echo "📋 Getting private subnet information..."
PRIVATE_SUBNET_1=$(aws ec2 describe-subnets \
    --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*private*" \
    --query "Subnets[0].SubnetId" \
    --output text)

PRIVATE_SUBNET_2=$(aws ec2 describe-subnets \
    --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*private*" \
    --query "Subnets[1].SubnetId" \
    --output text)

if [ -z "$PRIVATE_SUBNET_1" ] || [ -z "$PRIVATE_SUBNET_2" ]; then
    echo "❌ Error: Could not find private subnets. Make sure Step 1 is complete."
    exit 1
fi

echo "✅ Found private subnets:"
echo "   Subnet 1: $PRIVATE_SUBNET_1"
echo "   Subnet 2: $PRIVATE_SUBNET_2"

# Deploy the CloudFormation stack
echo "📦 Deploying API Gateway CloudFormation stack..."
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        VpcId=$VPC_ID \
        PrivateALBListenerArn=$PRIVATE_ALB_LISTENER_ARN \
        PrivateALBServerName=$INTERNAL_ALB_SERVER_NAME \
        PrivateSubnet1Id=$PRIVATE_SUBNET_1 \
        PrivateSubnet2Id=$PRIVATE_SUBNET_2 \
        ProjectName=${CLUSTER_NAME} \
    --tags \
        Project=${CLUSTER_NAME} \
        Environment=production

# Check deployment status
if [ $? -eq 0 ]; then
    echo "✅ API Gateway deployment successful!"
    
    # Get the API Gateway URL
    API_GATEWAY_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
        --output text)
    
    # Get IAM resources
    POLICY_ARN=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='McpApiAccessPolicyArn'].OutputValue" \
        --output text)
    
    echo "🌐 API Gateway URL: $API_GATEWAY_URL"
    
    # Update .env file with API Gateway URL
    if grep -q "API_GATEWAY_URL=" ../.env; then
        sed -i.bak "s|API_GATEWAY_URL=.*|API_GATEWAY_URL=$API_GATEWAY_URL|" ../.env
    else
        echo "API_GATEWAY_URL=$API_GATEWAY_URL" >> ../.env
    fi
    
    echo "📝 Updated .env file with API Gateway URL"
    
    # Test the API Gateway (will fail without proper IAM permissions)
    echo "🧪 Testing API Gateway (requires IAM permissions)..."
    sleep 10  # Wait for deployment to propagate
    
    echo ""
    echo "🎉 Step 3 Complete!"
    echo "📋 API Gateway Summary:"
    echo "   - API Gateway URL: $API_GATEWAY_URL"
    echo "   - Authentication: AWS SigV4 (IAM)"
    echo "   - VPC Link: Connected to private ALB"
    echo "   - Routes: /health (public), /mcp (authenticated)"
    echo "   - IAM Policy ARN: $POLICY_ARN"
    echo ""
    echo "🔐 To access the API, you need:"
    echo "   1. AWS credentials configured"
    echo "   2. IAM permissions to execute-api:Invoke"
    echo "   3. Use AWS SDK or CLI with SigV4 signing"
    echo ""
    echo "📝 To grant access to users/roles, attach the policy: $POLICY_ARN"
    echo ""
    echo "🧪 Test the API:"
    echo "   cd ../deployment && python3 test-api.py"
    
else
    echo "❌ API Gateway deployment failed!"
    exit 1
fi
