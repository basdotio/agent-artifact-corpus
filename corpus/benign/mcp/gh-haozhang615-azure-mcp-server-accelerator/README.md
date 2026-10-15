# Azure Container App MCP Server Solution Accelerator

Welcome to the **Azure Container App MCP Server Solution Accelerator**. This project provides a complete Model Context Protocol (MCP) server implementation with Azure Container Apps deployment using Azure Developer CLI (`azd`).

## 🎯 What This Solution Provides

This solution accelerator creates a complete MCP server that:
- Implements a simple slogan creation tool: `Microsoft = {word}`
- Runs as a containerized Python application
- Deploys to Azure Container Apps with full observability
- Uses Azure Developer CLI for one-command deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │───▶│  Container App   │───▶│  FastMCP Server │
│ (Copilot/Tools) │    │ (Azure hosting)  │    │ (Python Logic)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Azure Monitor    │
                       │ & App Insights   │
                       └──────────────────┘
```

## ⚙️ Prerequisites

Before you begin, ensure you have:

- **Visual Studio Code** installed ([link](https://code.visualstudio.com/download))
- **Python 3.11+** installed
- **Docker** installed ([link](http://aka.ms/azure-dev/docker-install))
- **Azure Developer CLI** installed ([link](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd))
- **Azure Subscription** (with payment method added)
- **GitHub account**

## 🚀 Quick Start

### 1. 🔐 Login to Azure

```bash
azd auth login
```

### 2. 📦 Deploy the Solution

```bash
azd up
```

**That's it!** You'll only be asked for:
- ✅ **Environment name** - A unique identifier for your deployment (e.g., "my-mcp-server")
- ✅ **Azure region** - Choose from available regions (e.g., "East US 2")

No other configuration needed! The `azd up` command will:
1. 🏗️ Provision all Azure resources automatically (Container Apps, Container Registry, Monitoring)
2. 🐳 Build and containerize your Python MCP server
3. 🚀 Deploy the container to Azure Container Apps
4. 📊 Configure networking and monitoring
5. 🔗 Provide your server endpoint URL

### 3. ✅ Test Your Deployment

After deployment completes, you'll see output similar to:
```
✅ Your application was provisioned and deployed to Azure
🔗 Container App Endpoint: https://slogan-mcp-python.kindwater-12345678.eastus.azurecontainerapps.io
```

Test the MCP endpoint:
```bash
curl https://your-app-url.azurecontainerapps.io/mcp
```

You should see: `{"jsonrpc":"2.0","error":{"code":-32000,"message":"Not Acceptable: Client must accept text/event-stream"}}`

This confirms your MCP server is running correctly!

## 🔧 Local Development

### Run Locally

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Run the server:**
   ```bash
   python main.py
   ```

3. **Test locally:**
   ```bash
   curl http://localhost:3000/mcp
   ```

## 🛠️ Using Your MCP Server

### In Visual Studio Code with GitHub Copilot

1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type `MCP` and select `MCP: Add Server...`
3. Select `HTTP (HTTP or Server-Sent Events)`
4. Enter your server URL: `https://your-app-url.azurecontainerapps.io/mcp`
5. Give it a name: `my-test-mcp-server`
6. Save to either Global or Workspace scoped settings

### In Microsoft Copilot Studio

1. Follow the [MCP connector setup guide](https://aka.ms/mcsmcp)
2. Use your deployed Azure Container App URL as the host
3. Create an agent that uses the slogan creation tool
4. Test the agent in Copilot Studio, example result below:
    ![Copilot Studio Slogan Example](./images/copilot_studio_example.png)

## 📊 Monitoring & Observability

Your deployment includes:

- **Application Insights** for telemetry and performance monitoring
- **Log Analytics** for centralized logging
- **Azure Monitor** dashboards
- **Container Apps metrics** for scaling insights

Access monitoring in the Azure Portal:
1. Navigate to your Resource Group: `rg-{your-environment-name}`
2. Open Application Insights
3. View Live Metrics, Performance, and Logs

## 🔒 Security Features

This solution includes:

- **Managed Identity** for secure Azure resource access
- **Container Registry** with role-based access control
- **Network isolation** within Container Apps Environment
- **HTTPS-only** endpoints with built-in certificates

## 🧹 Cleanup

To remove all Azure resources:

```bash
azd down
```

Confirm with `y` when prompted. This will delete:
- Container Apps and Environment
- Container Registry
- Monitoring resources
- Resource Group

## 🏗️ Project Structure

```
mcp-aca/
├── main.py                 # MCP server implementation
├── pyproject.toml          # Python dependencies
├── Dockerfile             # Container configuration
├── azure.yaml             # Azure Developer CLI config
├── infra/                 # Infrastructure as Code
│   ├── main.bicep         # Main Bicep template
│   ├── resources.bicep    # Resource definitions
│   ├── abbreviations.json # Azure naming conventions
│   └── modules/
│       └── fetch-container-image.bicep
└── README.md              # This file
```

## 🎛️ Customization

### Adding New MCP Tools

Edit `main.py` to add more tools:

```python
@mcp.tool()
def another_tool(input: str) -> str:
    """Description of your new tool."""
    """function logic here"""
    return f"new logic that uses {input}"
```

### Scaling Configuration

Modify `infra/resources.bicep` to adjust scaling:

```bicep
scaleMinReplicas: 1    # Minimum instances
scaleMaxReplicas: 10   # Maximum instances
```

## 🔮 Outlook for Scaling

### Enterprise-Grade MCP Server Management with Azure API Management

As your MCP server ecosystem grows, this solution accelerator provides a foundation for enterprise-scale deployment and management through integration with **Azure API Management (APIM)** and **Azure API Center**.

[Preview MCP Center](https://mcp.azure.com/) – explore an Azure API Management powered directory for centralized MCP server discovery and governance.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure API Management                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   MCP Server    │ │   MCP Server    │ │   MCP Server    │   │
│  │   (Finance)     │ │   (Analytics)   │ │   (Content)     │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Azure API Center                           │
│  • Centralized API Discovery    • Policy Management            │
│  • Governance & Compliance      • Analytics & Monitoring       │
│  • Developer Portal             • Version Control              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Client Applications & AI Agents                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ Copilot     │ │ Custom      │ │ Power       │ │ Third     │ │
│  │ Studio      │ │ AI Agents   │ │ Platform    │ │ Party     │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Key Scaling Benefits

**🌐 GenAI Gateway Benefits**
- **Unified Entry Point**: Single endpoint for all MCP servers with intelligent routing
- **Rate Limiting**: Protect individual MCP servers from overload
- **Authentication & Authorization**: Centralized security with Azure AD integration
- **Caching**: Improve response times for frequently requested MCP operations
- **Transformation**: Standardize request/response formats across different MCP implementations

**📊 Central Management through Azure API Center**
- **API Discovery**: Catalog all MCP servers with searchable metadata and capabilities
- **Governance**: Enforce consistent naming, versioning, and documentation standards
- **Compliance**: Track API usage, monitor SLA compliance, and generate audit reports
- **Developer Experience**: Self-service portal for teams to discover and consume MCP servers

#### Implementation Roadmap

**Phase 1: API Management Integration**
```bicep
// Add to infra/resources.bicep
resource apiManagement 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: '${abbreviations.apiManagementService}${resourceToken}'
  location: location
  sku: {
    name: 'Developer'  // Scale to Standard/Premium for production
    capacity: 1
  }
  properties: {
    publisherEmail: 'admin@company.com'
    publisherName: 'MCP Server Team'
  }
}

// MCP Server API Configuration
resource mcpApi 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apiManagement
  name: 'mcp-servers'
  properties: {
    displayName: 'MCP Server Collection'
    path: 'mcp'
    protocols: ['https']
    serviceUrl: containerApp.properties.configuration.ingress.fqdn
  }
}
```

**Phase 2: Azure API Center Integration**
```bicep
resource apiCenter 'Microsoft.ApiCenter/services@2024-03-01' = {
  name: '${abbreviations.apiCenter}${resourceToken}'
  location: location
  properties: {
    // Centralized catalog for all MCP servers
  }
}

// Register MCP APIs in API Center
resource mcpApiRegistration 'Microsoft.ApiCenter/services/workspaces/apis@2024-03-01' = {
  parent: apiCenter
  name: 'mcp-slogan-server'
  properties: {
    title: 'Slogan Generation MCP Server'
    kind: 'rest'
    description: 'Model Context Protocol server for generating Microsoft-themed slogans'
    // Link to APIM backend
  }
}
```

**Phase 3: Multi-Server Deployment Pattern**
```yaml
# azure.yaml extension for multiple MCP servers
services:
  mcp-finance:
    project: ./servers/finance
    host: containerapp
    
  mcp-analytics:
    project: ./servers/analytics  
    host: containerapp
    
  mcp-content:
    project: ./servers/content
    host: containerapp

hooks:
  postdeploy:
    # Register all servers with API Center
    shell: |
      az apic api import --api-center-name $AZURE_API_CENTER_NAME \
        --workspace-name default \
        --api-id mcp-finance \
        --specification @servers/finance/openapi.json
```

#### Advanced Scaling Features

**🔄 Auto-Discovery & Registration**
- Implement MCP server auto-registration with API Center upon deployment
- Use Azure Event Grid to trigger catalog updates when new servers are deployed
- Automated OpenAPI specification generation from MCP tool definitions

**📈 Intelligent Load Balancing**
- Route requests based on MCP tool capabilities and current server load
- Implement circuit breaker patterns for resilient MCP server communication
- Geographic distribution of MCP servers with APIM regions

**🔐 Enterprise Security & Governance**
- OAuth 2.0 / Entra ID integration for MCP client authentication
- Role-based access control (RBAC) for different MCP tool categories
- API versioning strategies for backwards compatibility
- Audit logging and compliance reporting

**📊 Observability & Analytics**
- Consolidated monitoring across all MCP servers through Application Insights
- Custom dashboards showing MCP tool usage patterns and performance metrics
- Proactive alerting for MCP server health and capacity planning

This foundation enables you to build a robust, enterprise-ready MCP server ecosystem that can scale to hundreds of specialized AI tools while maintaining governance, security, and observability.

## 🤝 Contributing

This solution accelerator welcomes contributions and suggestions. To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues and questions:

1. Check the [troubleshooting section](#troubleshooting) below
2. Review Azure Container Apps documentation
3. Open an issue in this repository

## 🔧 Troubleshooting

### Common Issues

**Deployment fails with authentication error:**
```bash
azd auth login
azd up
```

**Container fails to start:**
- Check logs in Azure Portal: Container Apps → Monitoring → Log Stream

**Local development issues:**
```bash
# Reinstall dependencies
pip install --force-reinstall -e .

# Check Python version
python --version  # Should be 3.11+
```

## 📚 Learn More

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/introduction)
- [Azure Container Apps Documentation](https://docs.microsoft.com/azure/container-apps/)
- [Azure Developer CLI Documentation](https://docs.microsoft.com/azure/developer/azure-developer-cli/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for the Azure community**
