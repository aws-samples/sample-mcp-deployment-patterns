#!/usr/bin/env python3
"""
Silent token generator for serverless deployment - outputs only the ID token
Reads credentials from environment variables set by the wrapper script
"""
import boto3
import os
import sys

# Required environment variables
STACK_NAME = os.getenv('STACK_NAME')
REGION = os.getenv('REGION')
USERNAME = os.getenv('COGNITO_USERNAME')
PASSWORD = os.getenv('COGNITO_PASSWORD')

if not all([STACK_NAME, REGION, USERNAME, PASSWORD]):
    print("ERROR: Required environment variables not set", file=sys.stderr)
    print("  STACK_NAME, REGION, COGNITO_USERNAME, COGNITO_PASSWORD", file=sys.stderr)
    sys.exit(1)

try:
    # Query CloudFormation for Cognito configuration
    cfn = boto3.client('cloudformation', region_name=REGION)
    response = cfn.describe_stacks(StackName=STACK_NAME)
    outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
    
    USER_POOL_ID = outputs['CognitoUserPoolId']
    CLIENT_ID = outputs['CognitoUserPoolClientId']

except KeyError as e:
    print(f"ERROR: CloudFormation output not found: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to query CloudFormation: {e}", file=sys.stderr)
    sys.exit(1)

try:
    # Get ID token from Cognito
    cognito = boto3.client('cognito-idp', region_name=REGION)
    auth_response = cognito.initiate_auth(
        ClientId=CLIENT_ID,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': USERNAME,
            'PASSWORD': PASSWORD
        }
    )
    
    print(auth_response['AuthenticationResult']['IdToken'])

except cognito.exceptions.NotAuthorizedException:
    print("ERROR: Invalid username or password", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Cognito authentication failed: {e}", file=sys.stderr)
    sys.exit(1)
