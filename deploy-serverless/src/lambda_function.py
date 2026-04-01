import json
import logging
from mcp_server import mcp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda handler for MCP server
    Integrates lightweight MCP implementation with API Gateway Lambda Proxy integration
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Handle health check
        if event.get('httpMethod') == 'GET' and event.get('path') == '/':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'healthy',
                    'service': 'maths-mcp-server',
                    'version': '2.0.0',
                    'framework': 'Lightweight MCP'
                })
            }

        # Handle OPTIONS requests (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                },
                'body': ''
            }

        # Handle MCP requests using lightweight MCP server
        if event.get('httpMethod') == 'POST' and event.get('path') == '/mcp':
            body = json.loads(event.get('body', '{}'))
            method = body.get('method')

            if method == 'tools/list':
                # Get tools list from MCP server
                tools_list = mcp.get_tools()

                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'jsonrpc': '2.0',
                        'id': body.get('id'),
                        'result': {
                            'tools': tools_list
                        }
                    })
                }

            elif method == 'tools/call':
                # Call tool using MCP server
                params = body.get('params', {})
                tool_name = params.get('name')
                arguments = params.get('arguments', {})

                try:
                    result = mcp.call_tool(tool_name, arguments)

                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'jsonrpc': '2.0',
                            'id': body.get('id'),
                            'result': {
                                'content': [
                                    {
                                        'type': 'text',
                                        'text': str(result)
                                    }
                                ]
                            }
                        })
                    }
                except ValueError as ve:
                    # Tool not found
                    logger.error(f"Tool not found: {str(ve)}")
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'jsonrpc': '2.0',
                            'id': body.get('id'),
                            'error': {
                                'code': -32601,
                                'message': str(ve)
                            }
                        })
                    }
                except Exception as tool_error:
                    logger.error(f"Tool execution error: {str(tool_error)}")
                    return {
                        'statusCode': 500,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'jsonrpc': '2.0',
                            'id': body.get('id'),
                            'error': {
                                'code': -32603,
                                'message': f'Tool execution failed: {str(tool_error)}'
                            }
                        })
                    }

            else:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'jsonrpc': '2.0',
                        'id': body.get('id'),
                        'error': {
                            'code': -32601,
                            'message': f'Unknown method: {method}'
                        }
                    })
                }

        # Default response for unhandled requests
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Not found',
                'path': event.get('path'),
                'method': event.get('httpMethod')
            })
        }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def _get_input_schema(tool_func):
    """
    Extract input schema from tool function annotations
    """
    import inspect
    from typing import get_type_hints

    try:
        # Get function signature
        sig = inspect.signature(tool_func)
        type_hints = get_type_hints(tool_func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_type = type_hints.get(param_name, str)

            # Map Python types to JSON Schema types
            json_type = 'string'
            if param_type == int:
                json_type = 'integer'
            elif param_type == float:
                json_type = 'number'
            elif param_type == bool:
                json_type = 'boolean'

            properties[param_name] = {
                'type': json_type,
                'description': f'{param_name} parameter'
            }

            # Check if parameter is required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            'type': 'object',
            'properties': properties,
            'required': required
        }
    except Exception as e:
        logger.warning(f"Could not extract schema for {tool_func.__name__}: {e}")
        return {
            'type': 'object',
            'properties': {},
            'required': []
        }
