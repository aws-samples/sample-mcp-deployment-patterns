#!/bin/bash

# Cleanup Script
# Removes all deployed resources in reverse order

set -e

echo "🧹 EKS MCP Server Cleanup"
echo "========================="

# Load environment variables
if [ -f "../.env" ]; then
    source ../.env
else
    echo "❌ Error: .env file not found in parent directory"
    exit 1
fi

echo "⚠️  This will DELETE all deployed resources:"
echo "   - API Gateway and IAM policies"
echo "   - EKS workloads and ALBs"
echo "   - EKS cluster and infrastructure"
echo "   - ECR repository and images"
echo ""

read -p "🤔 Are you sure you want to delete everything? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

echo ""
echo "🗑️  Starting cleanup..."

# Step 1: Delete API Gateway
echo "🗑️  Deleting API Gateway..."
aws cloudformation delete-stack --stack-name "${CLUSTER_NAME}-api-gateway" --region $REGION 2>/dev/null || echo "API Gateway stack not found"

# Step 2: Delete Kubernetes resources
echo "🗑️  Deleting Kubernetes workloads..."
if kubectl get namespace $NAMESPACE >/dev/null 2>&1; then
    kubectl delete namespace $NAMESPACE --ignore-not-found=true
    echo "⏳ Waiting for namespace deletion..."
    kubectl wait --for=delete namespace/$NAMESPACE --timeout=300s 2>/dev/null || echo "Namespace deletion timeout"
fi

# Step 3: Delete EKS Infrastructure
echo "🗑️  Deleting EKS infrastructure..."
aws cloudformation delete-stack --stack-name "${CLUSTER_NAME}-infrastructure" --region $REGION 2>/dev/null || echo "Infrastructure stack not found"

# Step 4: Delete ECR repository
echo "🗑️  Deleting ECR repository..."
aws ecr delete-repository --repository-name $ECR_REPOSITORY --region $REGION --force 2>/dev/null || echo "ECR repository not found"

# Wait for CloudFormation stacks to be deleted
echo "⏳ Waiting for CloudFormation stacks to be deleted..."
echo "   This may take 10-15 minutes..."

# Wait for API Gateway stack
aws cloudformation wait stack-delete-complete --stack-name "${CLUSTER_NAME}-api-gateway" --region $REGION 2>/dev/null || echo "API Gateway stack deletion complete"

# Wait for Infrastructure stack
aws cloudformation wait stack-delete-complete --stack-name "${CLUSTER_NAME}-infrastructure" --region $REGION 2>/dev/null || echo "Infrastructure stack deletion complete"

echo ""
echo "✅ Cleanup complete!"
echo "📋 All resources have been deleted:"
echo "   ✅ API Gateway and IAM policies"
echo "   ✅ EKS cluster and workloads"
echo "   ✅ VPC and networking"
echo "   ✅ ECR repository"
echo ""
echo "💡 You may want to clean up any remaining:"
echo "   - Docker images on your local machine"
echo "   - AWS CLI configuration if no longer needed"