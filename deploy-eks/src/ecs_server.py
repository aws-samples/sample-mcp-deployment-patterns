#!/usr/bin/env python3
"""
ECS HTTP MCP Server for Math Operations
HTTP server that implements MCP protocol for ECS deployment
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import socket
from mcp_server import mcp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPHandler(BaseHTTPRequestHandler):
    """HTTP handler for MCP requests"""
    
    def do_GET(self):
        """Handle GET requests (health check)"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/' or parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'healthy',
                'service': 'maths-mcp-server',
                'version': '2.0.0',
                'framework': 'ECS MCP',
                'hostname': socket.gethostname(),
                'container_id': os.getenv('HOSTNAME', 'unknown')
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests (MCP calls)"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/mcp':
            try:
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                request_data = json.loads(body)
                
                logger.info(f"Received MCP request: {request_data}")
                
                method = request_data.get('method')
                
                if method == 'tools/list':
                    # Get tools list from MCP server
                    tools_list = mcp.get_tools()
                    
                    response = {
                        'jsonrpc': '2.0',
                        'id': request_data.get('id'),
                        'result': {
                            'tools': tools_list
                        }
                    }
                    
                elif method == 'tools/call':
                    # Call tool using MCP server
                    params = request_data.get('params', {})
                    tool_name = params.get('name')
                    arguments = params.get('arguments', {})
                    
                    try:
                        result = mcp.call_tool(tool_name, arguments)
                        
                        response = {
                            'jsonrpc': '2.0',
                            'id': request_data.get('id'),
                            'result': {
                                'content': [
                                    {
                                        'type': 'text',
                                        'text': str(result)
                                    }
                                ]
                            }
                        }
                        
                    except ValueError as ve:
                        response = {
                            'jsonrpc': '2.0',
                            'id': request_data.get('id'),
                            'error': {
                                'code': -32601,
                                'message': str(ve)
                            }
                        }
                        
                    except Exception as tool_error:
                        logger.error(f"Tool execution error: {str(tool_error)}")
                        response = {
                            'jsonrpc': '2.0',
                            'id': request_data.get('id'),
                            'error': {
                                'code': -32603,
                                'message': f'Tool execution failed: {str(tool_error)}'
                            }
                        }
                
                else:
                    response = {
                        'jsonrpc': '2.0',
                        'id': request_data.get('id'),
                        'error': {
                            'code': -32601,
                            'message': f'Unknown method: {method}'
                        }
                    }
                
                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}", exc_info=True)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_response = {
                    'error': 'Internal server error',
                    'message': str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_error(404)

def main():
    """Main entry point"""
    port = int(os.getenv('PORT', 8000))
    
    # The pod is reached through a ClusterIP service and an internal ALB.
    server = HTTPServer(('0.0.0.0', port), MCPHandler)  # nosec B104
    
    logger.info(f"Starting ECS MCP Server on port {port}")
    logger.info(f"Health check: http://0.0.0.0:{port}/")
    logger.info(f"MCP endpoint: http://0.0.0.0:{port}/mcp")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.shutdown()

if __name__ == "__main__":
    main()
