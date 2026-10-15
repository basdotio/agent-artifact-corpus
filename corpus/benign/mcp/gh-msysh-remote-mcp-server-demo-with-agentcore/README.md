# MCP Server Demo with Amazon Bedrock AgentCore Runtime

[日本語の情報](https://blog.msysh.me/posts/2025/07/amazon-bedrock-agentcore-runtime-mcp-server-deployment.html)

This project demonstrates how to deploy a Model Context Protocol (MCP) server to Amazon Bedrock AgentCore Runtime. It includes a test agent that connects from Strands Agents to the MCP server.

> [!IMPORTANT]
> Amazon Bedrock AgentCore is Preview status as of July 2025.

## Project Overview

The demo consists of two main components:

1. **MCP Server**: A FastMCP server with simple tools deployed to Amazon Bedrock AgentCore Runtime
2. **Test Client**: A Strands Agents-based client that connects to the deployed MCP server

## Prerequisites

- Python 3.13 or higher
- AWS CLI configured with appropriate permissions
- Amazon Bedrock AgentCore Runtime access
- [uv](https://github.com/astral-sh/uv) for Python package management

## Project Structure

```
my-mcp-server/
├── test-mcp-client/       # Test client using Strands Agents
│   ├── agent.py           # Client implementation
│   └── pyproject.toml     # Client dependencies
├── util/
│   └── cognito-setup.sh   # Script to set up Cognito authentication
├── Dockerfile             # Container definition for deployment
├── main.py               # MCP server implementation
├── pyproject.toml        # Server dependencies
└── README.md             # This file
```

## MCP Server

The MCP server (`main.py`) implements a simple FastMCP server with three tools:
- `add_numbers`: Adds two numbers
- `multiply_numbers`: Multiplies two numbers
- `greet_user`: Greets a user by name

The server is configured to run with the "streamable-http" transport, which is compatible with Amazon Bedrock AgentCore Runtime.

## Setup and Deployment

### 1. Install Dependencies

```bash
uv sync
source .venv/bin/activate
```

### 2. Create IAM Execution Role for AgentCore Runtime

Create IAM Execution Role for AgentCore Runtime. Please see more detail at https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html

### 3. Set Up OAuth 2.0 Authentication

The MCP server requires OAuth 2.0 authentication, which is implemented using Amazon Cognito. Run the provided script to set up the authentication infrastructure:

```bash
cd util
chmod +x cognito-setup.sh
./cognito-setup.sh
```

> [!TIP]
> If you want to change the User Pool name, test user name, or password. Please modify [the script](./util/cognito-setup.sh).

```bash
REGION=us-east-1
POOL_NAME='MyUserPool'
CLIENT_NAME='MyClient'
USER_NAME='testuser'
TEMPORARY_PASSWORD='...'
PASSWORD='...'
```

This script will:
- Create a Cognito user pool for OAuth 2.0 authentication
- Create an app client with appropriate authentication flows
- Create a test user with credentials
- Output the necessary OAuth configuration values for the MCP server

> [!WARNING]
> Please note that by default, the generated Bearer Token expires in 1 hour.

### 4. Update AgentCore Configuration

You can configure and deploy AgentCore with `agentcore` command tool. If you cannot find `agentcore`, please install by following command:

```bash
uv add --dev bedrock-agentcore-starter-toolkit
uv sync
```

And then, configure for deployment.

```bash
# Execution Role for MCP Server (https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)
EXECUTION_ROLE_ARN=arn:aws:iam::{{ACCOUNT_ID}}:role/{{ROLE_NAME}}

# Cognito User Pool ID and Client ID
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx

# region
REGION=us-east-1

agentcore configure \
  --name my_mcp_server \
  --entrypoint main.py \
  --execution-role ${EXECUTION_ROLE_ARN} \
  --authorizer-config "{
    \"customJWTAuthorizer\": {
      \"discoveryUrl\": \"https://cognito-idp.${REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}/.well-known/openid-configuration\",
      \"allowedClients\": [\"${COGNITO_CLIENT_ID}\"]
    }
  }" \
  --protocol MCP
```

When you run the command above, you will be prompted for an ECR repository URI as shown below. For this demo, we'll use auto-creation, so just press Enter. If you want to use your own ECR repository, you can specify it using the `--ecr` command line option.

```
🏗️  ECR Repository
Press Enter to auto-create ECR repository, or provide ECR Repository URI to use existing
ECR Repository URI (or skip to auto-create):
```

Next, you'll be asked to specify the dependency file. Since we're using uv, specify `pyproject.toml`. If you're using pip, specify `requirements.txt`. (You can also pre-specify this using the `--requirements-file` option.)

```
🔍 Detected dependency file: pyproject.toml
Press Enter to use this file, or type a different path (use Tab for autocomplete):
Path or Press Enter to use detected dependency file:
```

When you run the `agentcore configure` command, it will create files like `.bedrock_agentcore.yaml` and `Dockerfile` in your folder, as AgentCore Runtime is deployed and executed as a container.

### 5. Deploy to AgentCore Runtime

```bash
agentcore launch
```

This will:
- Build the Docker container
- Push it to Amazon ECR
- Deploy the agent to Amazon Bedrock AgentCore Runtime

### 6. Get the Endpoint URL

After deployment, get your MCP server endpoint following:

```
https://bedrock-agentcore.{{REGION}}.amazonaws.com/runtimes/{{ENCODED_AGENT_ARN}}/invocations?qualifier=DEFAULT
```

`ENCODED_AGENT_ARN` is the ARN with `:` converted to `%3A` and `/` converted to `%2F`.

## Running the Test Client

The test client demonstrates how to connect to your deployed MCP server using Strands Agents.

### 1. Set Environment Variables

```bash
export MCP_SERVER_ENDPOINT='https://bedrock-agentcore.{{REGION}}.amazonaws.com/runtimes/{{ENCODED_AGENT_ARN}}/invocations?qualifier=DEFAULT'
export BEARER_TOKEN='your-cognito-access-token'
```

If your access token is expired, you can get a new token with following command:

```bash
# Authenticate User and capture Access Token
export BEARER_TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "${CLIENT_ID}" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME="${USER_NAME}",PASSWORD="${PASSWORD}" \
  --region ${REGION} | jq -r '.AuthenticationResult.AccessToken')

# Output the required values
echo "Bearer Token: ${BEARER_TOKEN}"
```

### 2. Run the Test Client

```bash
cd test-mcp-client
uv run agent.py
```

The test client will:
1. Connect to your MCP server
2. List available tools
3. Create a Strands Agent with those tools
4. Send a test prompt in Japanese asking for a greeting

## Cleanup

Delete following resources which are deployed this demo, via AWS Management Console or AWS CLI.
* Amazon Bedrock AgentCore Runtime
* ECR Repository
* Cognito User Pool
* IAM Role for AgentCore Runtime execution

## Security Considerations

- The MCP server uses JWT authentication via Amazon Cognito
- Make sure to properly manage your AWS credentials and tokens
- Consider implementing additional security measures for production use

## Troubleshooting

- If deployment fails, check your AWS credentials and permissions
- Verify that your Cognito configuration matches the values in `.bedrock_agentcore.yaml`
- Check AgentCore logs for detailed error information

## License

MIT