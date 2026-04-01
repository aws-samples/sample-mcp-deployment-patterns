#!/usr/bin/env python3
"""
ECS MCP Proxy with JWT Authentication
Connects to API Gateway endpoint with Cognito JWT token
"""

import asyncio
import os
import sys
import secrets
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Event
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
import requests
from dotenv import load_dotenv

# Load environment from ECS deployment
load_dotenv('../deploy-ecs/.env')

# Configuration
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
COGNITO_CLIENT_SECRET = os.getenv('COGNITO_CLIENT_SECRET')
COGNITO_REGION = os.getenv('COGNITO_REGION', 'us-west-2')
STACK_NAME = os.getenv('STACK_NAME', 'maths-mcp-ecs')

# OAuth endpoints
COGNITO_DOMAIN = f"{STACK_NAME}-auth.auth.{COGNITO_REGION}.amazoncognito.com"
AUTHORIZE_URL = f"https://{COGNITO_DOMAIN}/oauth2/authorize"
TOKEN_URL = f"https://{COGNITO_DOMAIN}/oauth2/token"
REDIRECT_URI = "http://localhost:8080/callback"

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP server to handle OAuth callback"""
    
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.server.auth_event.set()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h2>Success! You can close this window.</h2></body></html>')
        else:
            self.send_response(400)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def get_jwt_token_oauth():
    """Get JWT token using simple OAuth 2.0 Authorization Code flow"""
    try:
        print("🔐 Starting OAuth 2.0 flow...", file=sys.stderr)
        
        state = secrets.token_urlsafe(32)
        
        # Build authorization URL (no PKCE)
        auth_params = {
            'response_type': 'code',
            'client_id': COGNITO_CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'scope': 'openid email profile',
            'state': state
        }
        
        auth_url = f"{AUTHORIZE_URL}?" + urllib.parse.urlencode(auth_params)
        
        print(f"🌐 Opening browser for authentication...", file=sys.stderr)
        webbrowser.open(auth_url)
        
        # Start callback server
        server = HTTPServer(('localhost', 8080), CallbackHandler)
        server.auth_code = None
        server.auth_event = Event()
        
        server_thread = Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        print("⏳ Waiting for authentication callback...", file=sys.stderr)
        
        # Wait for authorization code with timeout
        if not server.auth_event.wait(timeout=120):
            server.shutdown()
            print("❌ Timeout waiting for authorization", file=sys.stderr)
            return None
        
        server.shutdown()
        
        print("✅ Authorization code received, exchanging for tokens...", file=sys.stderr)
        
        # Exchange code for tokens (no PKCE)
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': COGNITO_CLIENT_ID,
            'code': server.auth_code,
            'redirect_uri': REDIRECT_URI
        }
        
        if COGNITO_CLIENT_SECRET:
            token_data['client_secret'] = COGNITO_CLIENT_SECRET
        
        response = requests.post(
            TOKEN_URL,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Token exchange failed: {response.text}", file=sys.stderr)
            return None
        
        tokens = response.json()
        return tokens['id_token']
        
    except Exception as e:
        print(f"❌ OAuth flow error: {e}", file=sys.stderr)
        return None

# Get JWT token using OAuth flow
print("🔑 Getting JWT token via OAuth 2.0...", file=sys.stderr)
JWT_TOKEN = get_jwt_token_oauth()

if not JWT_TOKEN:
    print("❌ Failed to get JWT token via OAuth flow", file=sys.stderr)
    sys.exit(1)

print(f"🚀 ECS MCP Proxy - {API_GATEWAY_URL}/mcp", file=sys.stderr)
print(f"✅ JWT token obtained: {JWT_TOKEN[:50]}...", file=sys.stderr)

server = Server("ecs-mcp-proxy")

# Global token for refresh
current_token = JWT_TOKEN

@server.list_tools()
async def list_tools():
    """List available tools from ECS MCP server"""
    global current_token
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{API_GATEWAY_URL}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={
                    "Authorization": f"Bearer {current_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 401:
                # Token expired, get new one
                print("⚠️ Token expired, getting fresh token...", file=sys.stderr)
                current_token = get_jwt_token_oauth()
                if current_token:
                    response = await client.post(
                        f"{API_GATEWAY_URL}/mcp",
                        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                        headers={
                            "Authorization": f"Bearer {current_token}",
                            "Content-Type": "application/json"
                        }
                    )
            
            if response.status_code == 200:
                data = response.json()
                tools = []
                for tool_data in data["result"]["tools"]:
                    tools.append(Tool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        inputSchema=tool_data["inputSchema"]
                    ))
                return tools
            else:
                print(f"❌ Error listing tools: {response.status_code} - {response.text}", file=sys.stderr)
                return []
                
        except Exception as e:
            print(f"❌ Exception listing tools: {str(e)}", file=sys.stderr)
            return []

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Call a tool on the ECS MCP server"""
    global current_token
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{API_GATEWAY_URL}/mcp",
                json={
                    "jsonrpc": "2.0", 
                    "id": 2, 
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}
                },
                headers={
                    "Authorization": f"Bearer {current_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 401:
                # Token expired, get new one
                print("⚠️ Token expired, getting fresh token...", file=sys.stderr)
                current_token = get_jwt_token_oauth()
                if current_token:
                    response = await client.post(
                        f"{API_GATEWAY_URL}/mcp",
                        json={
                            "jsonrpc": "2.0", 
                            "id": 2, 
                            "method": "tools/call",
                            "params": {"name": name, "arguments": arguments}
                        },
                        headers={
                            "Authorization": f"Bearer {current_token}",
                            "Content-Type": "application/json"
                        }
                    )
            
            if response.status_code == 200:
                data = response.json()
                return [TextContent(type="text", text=item["text"]) 
                       for item in data["result"]["content"]]
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Error calling tool: {error_msg}", file=sys.stderr)
                return [TextContent(type="text", text=f"Error: {error_msg}")]
                
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"❌ Exception calling tool: {error_msg}", file=sys.stderr)
            return [TextContent(type="text", text=f"Error: {error_msg}")]

async def main():
    """Main server loop"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())