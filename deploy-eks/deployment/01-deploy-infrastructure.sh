#!/bin/bash

# Step 1: Deploy EKS Infrastructure
# This script deploys the EKS cluster, VPC, subnets, and AWS Load Balancer Controller

set -e

echo "🚀 Step 1: Deploying EKS Infrastructure"
echo "========================================"

# Load environment variables
if [ -f "../.env" ]; then
    source ../.env
else
    echo "❌ Error: .env file not found in parent directory"
    echo "💡 Please run this script from the deployment/ directory"
    exit 1
fi

# Set default values
STACK_NAME="${CLUSTER_NAME}-infrastructure"
TEMPLATE_FILE="../infrastructure/cloudformation.yaml"

echo "📋 Configuration:"
echo "   Cluster Name: $CLUSTER_NAME"
echo "   Region: $REGION"
echo "   Stack Name: $STACK_NAME"
echo ""

# Check if CloudFormation template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "❌ Error: CloudFormation template not found at $TEMPLATE_FILE"
    exit 1
fi

# Deploy the CloudFormation stack
echo "📦 Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        ClusterName=$CLUSTER_NAME \
        Region=$REGION \
    --tags \
        Project=$CLUSTER_NAME \
        Environment=production

# Check deployment status
if [ $? -eq 0 ]; then
    echo "✅ Infrastructure deployment successful!"
    
    # Get VPC ID and update .env file
    VPC_ID=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue" \
        --output text)
    
    if [ -n "$VPC_ID" ]; then
        echo "🌐 VPC ID: $VPC_ID"
        
        # Update .env file with VPC ID
        if grep -q "VPC_ID=" ../.env; then
            sed -i.bak "s|VPC_ID=.*|VPC_ID=$VPC_ID|" ../.env
        else
            echo "VPC_ID=$VPC_ID" >> ../.env
        fi
        
        echo "📝 Updated .env file with VPC ID"
    fi
    
    echo ""
    echo "🎉 Step 1 Complete!"
    echo "📋 Infrastructure Summary:"
    echo "   - EKS Cluster: $CLUSTER_NAME"
    echo "   - VPC ID: $VPC_ID"
    echo "   - Region: $REGION"
    echo ""
    echo "➡️  Next: Run ./02-deploy-workload.sh"
    
else
    echo "❌ Infrastructure deployment failed!"
    echo "🔍 Check the CloudFormation console for details"
    exit 1
fi