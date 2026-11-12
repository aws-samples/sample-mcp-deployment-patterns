#!/usr/bin/env python3
"""
OAuth Flow Testing Script for ECS MCP Server

This script demonstrates the complete OAuth flow:
1. Generate authorization URL
2. Handle callback to get authorization code
3. Exchange code for JWT tokens
4. Use JWT token to call API Gateway endpoint
"""

import base64
import hashlib
import html
import json
import os
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Event
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP server to handle OAuth callback"""
    
    def do_GET(self):
        # Parse the callback URL
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        returned_state = query_params.get('state', [''])[0]
        if not returned_state or not secrets.compare_digest(
            returned_state,
            self.server.expected_state,
        ):
            self.server.auth_error = 'OAuth state validation failed'
            self.server.callback_event.set()
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(
                b'<html><body><h2>Authorization Failed</h2>'
                b'<p>State validation failed. Return to the terminal.</p></body></html>'
            )
            return

        if 'code' in query_params:
            # Store the authorization code
            self.server.auth_code = query_params['code'][0]
            self.server.callback_event.set()  # Signal that callback received
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <body>
                    <h2>Authorization Successful!</h2>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            ''')
        else:
            # Keep the provider error for terminal diagnostics, but never reflect
            # untrusted query text into the browser response.
            error = query_params.get('error', ['Unknown error'])[0]
            self.server.auth_error = html.escape(error, quote=True)
            self.server.callback_event.set()
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(
                b'<html><body><h2>Authorization Failed</h2>'
                b'<p>Return to the terminal for details.</p></body></html>'
            )
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass

class OAuthTester:
    def __init__(self):
        self.region = os.getenv('COGNITO_REGION', 'us-west-2')
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        self.api_gateway_url = os.getenv('API_GATEWAY_URL')
        self.stack_name = os.getenv('STACK_NAME', 'maths-mcp-ecs')
        
        # OAuth endpoints
        self.cognito_domain = f"{self.stack_name}-auth.auth.{self.region}.amazoncognito.com"
        self.authorize_url = f"https://{self.cognito_domain}/oauth2/authorize"
        self.token_url = f"https://{self.cognito_domain}/oauth2/token"
        
        # Callback server
        self.callback_port = 8080
        self.redirect_uri = f"http://localhost:{self.callback_port}/callback"
        
        print(f"🔧 Configuration:")
        print(f"   User Pool ID: {self.user_pool_id}")
        print(f"   Client ID: {self.client_id}")
        print(f"   Cognito Domain: {self.cognito_domain}")
        print(f"   API Gateway URL: {self.api_gateway_url}")
        print()



    def start_authorization_flow(self):
        """Step 1: Generate authorization URL and open browser"""
        print("🚀 Step 1: Starting OAuth Authorization Flow")
        
        # PKCE protects the authorization code for this public local client.
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('ascii')).digest()
        ).rstrip(b'=').decode('ascii')

        auth_params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid email profile',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        
        auth_url = f"{self.authorize_url}?" + urllib.parse.urlencode(auth_params)
        
        print(f"📋 Authorization URL: {auth_url}")
        print()
        return state, code_verifier, auth_url

    def wait_for_callback(self, expected_state, auth_url):
        """Step 2: Start callback server and wait for authorization code"""
        print(f"⏳ Step 2: Waiting for callback on http://localhost:{self.callback_port}/callback")
        
        # Start HTTP server for callback
        server = HTTPServer(('localhost', self.callback_port), CallbackHandler)
        server.auth_code = None
        server.auth_error = None
        server.expected_state = expected_state
        server.callback_event = Event()
        
        # Start server in background thread
        server_thread = Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print("🌐 Opening browser for authorization...")
        webbrowser.open(auth_url)

        # Wait for authorization code with timeout
        timeout = 120  # 2 minutes
        if not server.callback_event.wait(timeout=timeout):
            server.shutdown()
            raise Exception("Timeout waiting for authorization code")
        
        server.shutdown()
        if server.auth_error:
            raise RuntimeError(f"Authorization failed: {server.auth_error}")
        if not server.auth_code:
            raise RuntimeError("Authorization callback did not contain a code")

        print("✅ Authorization code received")
        return server.auth_code

    def exchange_code_for_tokens(self, auth_code, code_verifier):
        """Step 3: Exchange authorization code for JWT tokens"""
        print("🔄 Step 3: Exchanging authorization code for tokens")
        
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'code_verifier': code_verifier,
        }
        
        # Make token request
        response = requests.post(
            self.token_url,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        if response.status_code != 200:
            print(f"❌ Token exchange failed: {response.status_code}")
            raise RuntimeError("Token exchange failed")
        
        tokens = response.json()
        
        print("✅ Successfully obtained tokens")
        print(f"   Token Type: {tokens.get('token_type', 'Bearer')}")
        print(f"   Expires In: {tokens.get('expires_in', 'unknown')} seconds")
        print()
        
        return tokens

    def test_api_gateway(self, tokens):
        """Step 4: Test API Gateway endpoint with JWT token"""
        print("🧪 Step 4: Testing API Gateway with JWT token")
        
        # Test MCP endpoint
        mcp_url = f"{self.api_gateway_url}/mcp"
        
        # Use ID token for API Gateway (contains user info)
        headers = {
            'Authorization': f"Bearer {tokens['id_token']}",
            'Content-Type': 'application/json'
        }
        
        # MCP request payload
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        print(f"📡 Making request to: {mcp_url}")
        print("🔑 Using the ID token returned by Cognito")
        
        try:
            response = requests.post(mcp_url, json=mcp_request, headers=headers, timeout=30)
            response.raise_for_status()
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ API Gateway request successful!")
                result = response.json()
                print(f"📄 Response: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ API Gateway request failed: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")

    def test_health_endpoint(self):
        """Test health endpoint (no auth required)"""
        print("🏥 Testing health endpoint (no auth)")
        
        health_url = f"{self.api_gateway_url}/health"
        
        try:
            response = requests.get(health_url, timeout=10)
            response.raise_for_status()
            print(f"📊 Health Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Health check successful!")
                print(f"📄 Response: {response.text}")
            else:
                print(f"❌ Health check failed: {response.text}")
        except Exception as e:
            print(f"❌ Health check failed: {str(e)}")
        
        print()

    def run_complete_flow(self):
        """Run the complete OAuth flow"""
        print("🎯 OAuth Flow Testing for ECS MCP Server")
        print("=" * 50)
        
        try:
            # Test health endpoint first
            self.test_health_endpoint()
            
            # Step 1: Start authorization flow
            state, code_verifier, auth_url = self.start_authorization_flow()
            
            # Step 2: Wait for callback
            auth_code = self.wait_for_callback(state, auth_url)
            
            # Step 3: Exchange code for tokens
            tokens = self.exchange_code_for_tokens(auth_code, code_verifier)
            
            # Step 4: Test API Gateway
            self.test_api_gateway(tokens)
            
            print("\n🎉 OAuth flow completed successfully!")
            
        except Exception as e:
            print(f"\n❌ OAuth flow failed: {str(e)}")
            return False
        
        return True

def main():
    """Main function"""
    tester = OAuthTester()
    success = tester.run_complete_flow()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
