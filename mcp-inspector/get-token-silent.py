#!/usr/bin/env python3
"""
Silent token generator - outputs only the access token
Used by start-oauth-proxy.sh to automatically get fresh tokens
"""

import boto3
import sys
import os
import hmac
import hashlib
import base64

# Read from environment variables (loaded from .env by wrapper script)
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
REGION = os.getenv("COGNITO_REGION")
USERNAME = os.getenv("COGNITO_USERNAME")
PASSWORD = os.getenv("COGNITO_PASSWORD")

if not all([USER_POOL_ID, CLIENT_ID, CLIENT_SECRET, REGION, USERNAME, PASSWORD]):
    print("ERROR: Missing required environment variables. Ensure .env file is configured.", file=sys.stderr)
    sys.exit(1)

def get_secret_hash(username, client_id, client_secret):
    """Calculate SECRET_HASH for Cognito"""
    message = bytes(username + client_id, 'utf-8')
    secret = bytes(client_secret, 'utf-8')
    dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

try:
    client = boto3.client('cognito-idp', region_name=REGION)
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

    # Output only the access token (to stdout)
    access_token = response['AuthenticationResult']['AccessToken']
    print(access_token)

except Exception as e:
    print(f"ERROR: Failed to get token: {e}", file=sys.stderr)
    sys.exit(1)
