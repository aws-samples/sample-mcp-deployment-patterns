#!/bin/bash

# Step 2: Deploy MCP Server Workload to EKS
# This script builds the Docker image, pushes to ECR, and deploys to EKS

set -e

echo "🚀 Step 2: Deploying MCP Server Workload to EKS"
echo "==============================================="

# Load environment variables
if [ -f "../.env" ]; then
    source ../.env
else
    echo "❌ Error: .env file not found in parent directory"
    echo "💡 Please run this script from the deployment/ directory"
    exit 1
fi

echo "📋 Configuration:"
echo "   Cluster Name: $CLUSTER_NAME"
echo "   Region: $REGION"
echo "   Namespace: $NAMESPACE"
echo "   Image: $IMAGE_NAME"
echo "   Replicas: $REPLICAS"
echo ""

# Check if EKS cluster exists
echo "🔍 Checking EKS cluster..."
if ! aws eks describe-cluster --name $CLUSTER_NAME --region $REGION >/dev/null 2>&1; then
    echo "❌ Error: EKS cluster '$CLUSTER_NAME' not found"
    echo "💡 Please run ./01-deploy-infrastructure.sh first"
    exit 1
fi

echo "✅ EKS cluster found"

# Update kubeconfig
echo "🔧 Updating kubeconfig..."
aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME

# Check if we can connect to the cluster
echo "🔍 Testing cluster connection..."
if ! kubectl get nodes >/dev/null 2>&1; then
    echo "❌ Error: Cannot connect to EKS cluster"
    echo "💡 Check your AWS credentials and cluster status"
    exit 1
fi

echo "✅ Connected to EKS cluster"

# Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $REGION >/dev/null 2>&1 || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $REGION

# Get ECR login token
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com

# Build and push Docker image
echo "🏗️  Building Docker image..."
docker build -t $IMAGE_NAME ../

# Tag and push to ECR
ECR_URI=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:latest
echo "📤 Pushing to ECR: $ECR_URI"
docker tag $IMAGE_NAME:latest $ECR_URI
docker push $ECR_URI

# Resolve image digest for immutable reference (CKV_K8S_43)
IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name $ECR_REPOSITORY \
    --region $REGION \
    --image-ids imageTag=latest \
    --query 'imageDetails[0].imageDigest' \
    --output text)
ECR_URI_DIGEST=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY@$IMAGE_DIGEST
echo "🔒 Digest-pinned image: $ECR_URI_DIGEST"

# Update .env with ECR URI (digest-pinned)
if grep -q "ECR_URI=" ../.env; then
    sed -i.bak "s|ECR_URI=.*|ECR_URI=$ECR_URI_DIGEST|" ../.env
else
    echo "ECR_URI=$ECR_URI_DIGEST" >> ../.env
fi

# Deploy to Kubernetes
echo "☸️  Deploying to Kubernetes..."

# Create namespace
kubectl apply -f ../k8s/namespace.yaml

# Update deployment with digest-pinned ECR URI (CKV_K8S_43)
sed "s|PLACEHOLDER_IMAGE_URI|$ECR_URI_DIGEST|g" ../k8s/deployment.yaml | kubectl apply -f -

# Apply service and ingress
kubectl apply -f ../k8s/service.yaml
kubectl apply -f ../k8s/ingress.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/maths-mcp-server -n $NAMESPACE --timeout=300s

# Check pod status
echo "📊 Checking pod status..."
kubectl get pods -n $NAMESPACE

# Get Internal ALB URL
echo "🌐 Getting Internal ALB URL..."
sleep 30  # Wait for ALB to be created

# Get internal ALB URL
INTERNAL_ALB_URL=$(kubectl get ingress maths-mcp-server-internal -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
if [ -n "$INTERNAL_ALB_URL" ]; then
    INTERNAL_ALB_URL="http://$INTERNAL_ALB_URL"
    echo "🔒 Internal ALB URL: $INTERNAL_ALB_URL"
    
    # Update .env file
    if grep -q "INTERNAL_ALB_URL=" ../.env; then
        sed -i.bak "s|INTERNAL_ALB_URL=.*|INTERNAL_ALB_URL=$INTERNAL_ALB_URL|" ../.env
    else
        echo "INTERNAL_ALB_URL=$INTERNAL_ALB_URL" >> ../.env
    fi
else
    echo "⏳ Internal ALB URL not available yet (will be available shortly)"
fi

echo ""
echo "🎉 Step 2 Complete!"
echo "📋 Workload Summary:"
echo "   - Docker Image: $ECR_URI_DIGEST"
echo "   - Namespace: $NAMESPACE"
echo "   - Replicas: $REPLICAS"
echo "   - Internal ALB: $INTERNAL_ALB_URL"
echo ""
echo "🔒 Security Note: Only internal ALB created for secure access via API Gateway"
echo "➡️  Next: Run ./03-deploy-api-gateway.sh"