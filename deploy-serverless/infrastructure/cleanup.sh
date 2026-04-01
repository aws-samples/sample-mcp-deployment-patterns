#!/bin/bash

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

STACK_NAME=${STACK_NAME:-maths-mcp-server}
REGION=${REGION:-us-east-1}

# Check AWS credentials
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    echo "Error: AWS credentials not configured"
    exit 1
fi

echo "This will delete all resources for stack: $STACK_NAME"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 1
fi

# Delete CloudFormation stack
echo "Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
echo "✓ Stack deleted"

# Delete S3 bucket if auto-created
S3_BUCKET_PATTERN="${STACK_NAME}-deployment-"
BUCKETS=$(aws s3api list-buckets --query "Buckets[?starts_with(Name, '${S3_BUCKET_PATTERN}')].Name" --output text 2>/dev/null || echo "")

if [ -n "$BUCKETS" ]; then
    for BUCKET in $BUCKETS; do
        echo "Deleting S3 bucket: $BUCKET..."
        aws s3 rb s3://$BUCKET --force
        echo "✓ Bucket deleted"
    done
fi

echo ""
echo "Cleanup complete. Run ./deploy.sh to deploy again."
