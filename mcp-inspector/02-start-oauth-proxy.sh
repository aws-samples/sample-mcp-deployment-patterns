#!/bin/bash
# Wrapper script to automatically get fresh OAuth token and launch proxy
# Credentials are loaded from .env file

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load environment variables from .env file
if [ -f "$SCRIPT_DIR/../deploy-agentcore-oauth/.env" ]; then
    echo "Loading credentials from .env..." >&2
    export $(grep -v '^#' "$SCRIPT_DIR/../deploy-agentcore-oauth/.env" | xargs)
else
    echo "ERROR: .env file not found!" >&2
    echo "Copy .env.example to .env and configure your credentials" >&2
    exit 1
fi

# Generate fresh OAuth token
echo "Getting fresh OAuth token..." >&2
BEARER_TOKEN=$(python3 "$SCRIPT_DIR/get-token-silent.py")

if [ -z "$BEARER_TOKEN" ]; then
    echo "ERROR: Failed to get OAuth token" >&2
    exit 1
fi

echo "✓ Token obtained successfully" >&2
export BEARER_TOKEN

# Launch the OAuth proxy
exec python3 "$SCRIPT_DIR/agentcore-proxy-oauth.py"
