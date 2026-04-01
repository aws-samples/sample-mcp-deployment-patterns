#!/usr/bin/env python3
"""
Lightweight MCP Server for Math Operations
Minimal implementation without heavy FastMCP dependencies for ECS
"""

class SimpleMCPServer:
    """
    Lightweight MCP server implementation using decorator pattern
    Similar to FastMCP but without the heavy dependencies
    """
    def __init__(self, name):
        self.name = name
        self._tools = {}

    def tool(self):
        """Decorator to register tools"""
        def decorator(func):
            self._tools[func.__name__] = func
            return func
        return decorator

    def get_tools(self):
        """Get list of registered tools"""
        tools = []
        for name, func in self._tools.items():
            tools.append({
                'name': name,
                'description': func.__doc__ or f"{name} tool",
                'inputSchema': self._get_input_schema(func)
            })
        return tools

    def call_tool(self, name, arguments):
        """Call a registered tool"""
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        return self._tools[name](**arguments)

    def _get_input_schema(self, func):
        """Extract input schema from function annotations"""
        import inspect
        from typing import get_type_hints

        try:
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

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

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            return {
                'type': 'object',
                'properties': properties,
                'required': required
            }
        except Exception:
            return {
                'type': 'object',
                'properties': {},
                'required': []
            }


# Create MCP server instance
mcp = SimpleMCPServer("maths")

# Register tools using decorator pattern (same as FastMCP)
@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers together"""
    return a * b

@mcp.tool()
def divide_numbers(a: float, b: float) -> float:
    """Divide two numbers"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

@mcp.tool()
def power_numbers(base: float, exponent: float) -> float:
    """Raise base to the power of exponent"""
    return base ** exponent

@mcp.tool()
def greet_user(name: str) -> str:
    """Greet a user by name"""
    return f"Hello, {name}! Nice to meet you from ECS."

# Export the mcp instance
__all__ = ['mcp']