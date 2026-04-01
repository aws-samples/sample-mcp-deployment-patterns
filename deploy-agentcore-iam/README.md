# Amazon Bedrock AgentCore MCP Deployment

Deploy the Math MCP server to [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/) Runtime with OAuth authentication.

## Architecture

```
Client → Amazon Bedrock AgentCore Runtime → MCP Server (Container)
```

## Prerequisites

- AWS CLI configured
- Python 3.10+
- AgentCore CLI: `pip install bedrock-agentcore-starter-toolkit`

## Quick Start

### 1. Deploy to AgentCore

```bash
cd deploy-agentcore/infrastructure
./deploy.sh
```

### 2. Test with JWT Authentication

```bash
cd deploy-agentcore/infrastructure
JWT_TOKEN="your-jwt-token" ./test-agentcore.sh
```

See `infrastructure/README.md` for detailed deployment instructions and authentication setup.

## Project Structure

```
deploy-agentcore/
├── src/                      # Source code
│   ├── agentcore_mcp.py      # AgentCore MCP server
│   └── requirements.txt      # AgentCore dependencies
└── infrastructure/           # Infrastructure files
    ├── deploy.sh             # AgentCore deployment script
    ├── test-agentcore.sh     # Testing script
    ├── .env                  # Environment variables
    └── README.md             # Deployment guide
```

## Available Tools

- `add_numbers(a, b)` - Add two numbers
- `multiply_numbers(a, b)` - Multiply two numbers  
- `greet_user(name)` - Greet a user by name
