#!/usr/bin/env python3
"""
Get OAuth Access Token for AgentCore using Cognito
This token includes the client_id claim required by AgentCore
"""

import boto3
import json
import sys
import os
import hmac
import hashlib
import base64
from base64 import b64decode
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print("Warning: .env file not found. Using environment variables or defaults.", file=sys.stderr)

# Cognito Configuration
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
REGION = os.getenv("COGNITO_REGION")

# User credentials
USERNAME = os.getenv("COGNITO_USERNAME")
PASSWORD = os.getenv("COGNITO_PASSWORD")

# Validate required environment variables
required_vars = {
    "COGNITO_USER_POOL_ID": USER_POOL_ID,
    "COGNITO_CLIENT_ID": CLIENT_ID,
    "COGNITO_CLIENT_SECRET": CLIENT_SECRET,
    "COGNITO_REGION": REGION,
    "COGNITO_USERNAME": USERNAME
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
    print("Please configure them in the .env file", file=sys.stderr)
    sys.exit(1)

if not PASSWORD:
    PASSWORD = input(f"Enter password for {USERNAME}: ")

def get_secret_hash(username, client_id, client_secret):
    """Calculate SECRET_HASH for Cognito"""
    message = bytes(username + client_id, 'utf-8')
    secret = bytes(client_secret, 'utf-8')
    dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

client = boto3.client('cognito-idp', region_name=REGION)

try:
    # Initiate authentication
    print("Authenticating...")
    secret_hash = get_secret_hash(USERNAME, CLIENT_ID, CLIENT_SECRET)
    response = client.initiate_auth(
        ClientId=CLIENT_ID,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': USERNAME,
            'PASSWORD': PASSWORD,
            'SECRET_HASH': secret_hash
        }
    )

    # Get both tokens
    access_token = response['AuthenticationResult']['AccessToken']
    id_token = response['AuthenticationResult']['IdToken']

    print("\n✓ Successfully authenticated!")

    # Check which token has the required claims for AgentCore
    print("\n" + "="*80)
    print("Checking tokens for AgentCore requirements...")
    print("="*80)

    # Decode access token
    print("\nAccess Token Payload:")
    try:
        payload = access_token.split('.')[1]
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        decoded = b64decode(payload).decode('utf-8')
        access_token_data = json.loads(decoded)
        print(json.dumps(access_token_data, indent=2))

        has_client_id = 'client_id' in access_token_data
        has_aud = 'aud' in access_token_data
        print(f"\n✓ client_id: {'YES' if has_client_id else 'NO'}")
        print(f"✓ aud: {'YES' if has_aud else 'NO'}")
    except Exception as e:
        print(f"Could not decode access token: {e}")
        access_token_data = {}

    # Decode ID token
    print("\n" + "="*80)
    print("ID Token Payload:")
    try:
        payload = id_token.split('.')[1]
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        decoded = b64decode(payload).decode('utf-8')
        id_token_data = json.loads(decoded)
        print(json.dumps(id_token_data, indent=2))

        has_client_id = 'client_id' in id_token_data or 'aud' in id_token_data
        has_aud = 'aud' in id_token_data
        print(f"\n✓ client_id/aud: {'YES' if has_client_id else 'NO'}")
        print(f"✓ aud claim: {'YES' if has_aud else 'NO'}")
        if has_aud:
            print(f"  aud value: {id_token_data.get('aud')}")
    except Exception as e:
        print(f"Could not decode ID token: {e}")
        id_token_data = {}

    # Determine which token to use
    print("\n" + "="*80)
    print("RECOMMENDED TOKEN FOR AGENTCORE:")
    print("AgentCore requires the 'client_id' claim which is present in ACCESS token")
    print("="*80)
    print("\nACCESS TOKEN (use this for AgentCore):")
    print(access_token)
    print("\n" + "="*80)
    print("ID TOKEN (for reference):")
    print(id_token)
    selected_token = access_token

    print("\n" + "="*80)
    print("\nTo use this token:")
    print("1. Copy the TOKEN above")
    print("2. Update JWT_TOKEN in mcp-inspector/agentcore-proxy.py")
    print("3. Reconnect MCP Inspector")
    print("="*80)

except client.exceptions.NotAuthorizedException:
    print("\n✗ Authentication failed: Invalid username or password")
    sys.exit(1)
except client.exceptions.UserNotFoundException:
    print(f"\n✗ User not found: {USERNAME}")
    print("\nCreate a user first:")
    print(f"aws cognito-idp admin-create-user --user-pool-id {USER_POOL_ID} --username {USERNAME} --temporary-password TempPass123! --region {REGION}")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")

    # Check if USER_PASSWORD_AUTH is enabled
    print("\nTroubleshooting:")
    print(f"1. Ensure USER_PASSWORD_AUTH is enabled for app client {CLIENT_ID}")
    print("2. Run this command to check:")
    print(f"   aws cognito-idp describe-user-pool-client --user-pool-id {USER_POOL_ID} --client-id {CLIENT_ID} --region {REGION}")
    sys.exit(1)
