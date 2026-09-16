# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Skill Overview

This is a **Claude Code skill for programmatic HCP Terraform automation** - a specialized knowledge base that provides comprehensive documentation and TypeScript wrapper functions for automating Terraform Cloud and Terraform Enterprise operations via the HashiCorp Terraform MCP server.

**Purpose**: Enable Claude to help users automate HCP Terraform operations: creating workspaces, triggering runs, managing variables, searching registries (public and private), and orchestrating infrastructure-as-code workflows programmatically.

## Critical Distinction from Other Skills

Unlike the other skills in this marketplace (terraform-style-guide, terraform-test, terraform-stacks), this skill **includes executable code** alongside documentation:

- **Documentation**: SKILL.md provides comprehensive guides and examples
- **Executable Code**: `scripts/` directory contains 34 type-safe TypeScript wrapper functions
- **Runtime Dependency**: Requires Docker and the HashiCorp MCP server to execute

**Important**: Users must set up the MCP server separately. This skill provides the knowledge and wrapper code, not a running MCP server instance.

## Repository Structure

```
terraform-mcp-as-code/
├── plugin.json                      # Skill metadata
├── SKILL.md                         # Main comprehensive guide
├── CLAUDE.md                        # This file - Claude-specific guidance
├── README.md                        # User-facing documentation
└── scripts/                         # TypeScript wrapper functions (34 tools)
    ├── client.ts                    # MCP connection manager
    ├── organization/                # 2 tools: List orgs/projects
    │   ├── index.ts
    │   ├── listTerraformOrgs.ts
    │   └── listTerraformProjects.ts
    ├── workspaces/                  # 7 tools: Workspace management
    │   ├── index.ts
    │   ├── createWorkspace.ts
    │   ├── updateWorkspace.ts
    │   ├── listWorkspaces.ts
    │   ├── getWorkspaceDetails.ts
    │   ├── createWorkspaceTags.ts
    │   ├── readWorkspaceTags.ts
    │   └── createNoCodeWorkspace.ts
    ├── runs/                        # 3 tools: Run management
    │   ├── index.ts
    │   ├── createRun.ts
    │   ├── getRunDetails.ts
    │   └── listRuns.ts
    ├── variables/                   # 9 tools: Variable management
    │   ├── index.ts
    │   ├── createWorkspaceVariable.ts
    │   ├── updateWorkspaceVariable.ts
    │   ├── deleteWorkspaceVariable.ts
    │   ├── createVariableSet.ts
    │   ├── updateVariableSet.ts
    │   ├── createVariableInVariableSet.ts
    │   ├── updateVariableInVariableSet.ts
    │   ├── deleteVariableInVariableSet.ts
    │   └── attachVariableSetToWorkspaces.ts
    ├── public-registry/             # 9 tools: Public registry access
    │   ├── index.ts
    │   ├── searchModules.ts
    │   ├── searchProviders.ts
    │   ├── searchPolicies.ts
    │   ├── getModuleDetails.ts
    │   ├── getProviderDetails.ts
    │   ├── getPolicyDetails.ts
    │   ├── getModuleReadme.ts
    │   ├── getProviderDocs.ts
    │   └── getProviderCapabilities.ts
    └── private-registry/            # 4 tools: Private registry access
        ├── index.ts
        ├── searchPrivateModules.ts
        ├── searchPrivateProviders.ts
        ├── getPrivateModuleDetails.ts
        └── getPrivateProviderDetails.ts
```

## Prerequisites and Environment Setup

### Required Environment

**For execution**, users need:
1. **Terraform Cloud/Enterprise account** with valid API token
2. **Docker** installed and running
3. **`TFE_TOKEN` environment variable** set with a valid Terraform API token
4. **Node.js** (if running TypeScript wrappers locally, though this is optional for Claude Code usage)

**MCP Server Command**:
```bash
docker run -i --rm -e TFE_TOKEN=your_token hashicorp/terraform-mcp-server
```

### Security Considerations

**Critical Security Guidelines**:

- **NEVER hardcode `TFE_TOKEN`** in code - always use environment variables
- **NEVER commit tokens** to version control
- **Use least-privilege tokens** - workspace-specific or org-specific when possible
- **Review generated code** before execution in production environments
- **Store tokens securely** in credential managers or environment configuration

**Example secure vs insecure code**:

```typescript
// ✅ Correct: Use environment variables
const token = process.env.TFE_TOKEN;

// ❌ Wrong: Hardcoded token
const token = "abc123..."; // NEVER DO THIS
```

## Tool Categories and Capabilities

### 1. Organization Tools (2 tools)

**Purpose**: Discover available Terraform organizations and projects

**Tools**:
- `listTerraformOrgs`: List all organizations the token has access to
- `listTerraformProjects`: List projects within a specific organization

**Common Use Case**: "Which organizations do I have access to?" or "What projects exist in my org?"

### 2. Workspace Tools (7 tools)

**Purpose**: Create, configure, update, and manage Terraform Cloud/Enterprise workspaces

**Tools**:
- `createWorkspace`: Create new workspace with configuration
- `updateWorkspace`: Modify workspace settings
- `listWorkspaces`: List workspaces in an organization
- `getWorkspaceDetails`: Get detailed workspace information
- `createWorkspaceTags`: Add tags to workspace
- `readWorkspaceTags`: Get workspace tags
- `createNoCodeWorkspace`: Create no-code module workspace

**Common Use Cases**:
- Setting up new environments (dev, staging, production)
- Configuring workspace settings (auto-apply, Terraform version)
- Organizing workspaces with tags

**Critical Parameters**:
- `workspace_name`: Unique workspace identifier
- `terraform_org_name`: Organization name
- `auto_apply`: "true" or "false" (string, not boolean)
- `execution_mode`: "remote", "local", or "agent"

### 3. Runs Tools (3 tools)

**Purpose**: Trigger and monitor Terraform runs programmatically

**Tools**:
- `createRun`: Trigger a new Terraform run
- `getRunDetails`: Get run status and output
- `listRuns`: List runs with filtering

**Common Use Cases**:
- Triggering deployments after code changes
- Monitoring run status and output
- Implementing CI/CD pipelines with Terraform

**Critical Parameters**:
- `run_type`: "plan-and-apply", "plan-only", "refresh-only", or "destroy"
- `message`: Description of why the run was triggered
- `auto_apply`: Whether to auto-apply after successful plan

### 4. Variables Tools (9 tools)

**Purpose**: Manage workspace variables and variable sets

**Tools**:
- Workspace Variables: create, update, delete
- Variable Sets: create, update, attach to workspaces
- Variable Set Variables: create, update, delete in variable sets

**Common Use Cases**:
- Setting environment-specific configuration
- Managing secrets and credentials
- Sharing common variables across workspaces

**Critical Parameters**:
- `key`: Variable name
- `value`: Variable value
- `category`: "terraform" (TF_VAR_*) or "env" (environment variable)
- `sensitive`: "true" to mark as sensitive (string, not boolean)
- `hcl`: "true" if value is HCL expression (string, not boolean)

**Security Note**: Always set `sensitive: "true"` for credentials, API keys, and secrets.

### 5. Public Registry Tools (9 tools)

**Purpose**: Search and access public Terraform Registry content

**Tools**:
- Search: modules, providers, policies
- Details: module, provider, policy details
- Documentation: module README, provider docs, provider capabilities

**Common Use Cases**:
- Finding the right module for infrastructure needs
- Researching provider capabilities
- Reading module documentation before usage

**Critical Parameters**:
- `module_query`, `provider_query`, `policy_query`: Search terms
- `module_id`, `provider_id`, `policy_id`: Full identifiers (e.g., "terraform-aws-modules/vpc/aws/5.1.2")

**Module ID Format**: `<namespace>/<name>/<provider>/<version>` (e.g., "terraform-aws-modules/vpc/aws/5.1.2")

### 6. Private Registry Tools (4 tools)

**Purpose**: Access private Terraform modules and providers in your organization

**Tools**:
- Search: private modules, private providers
- Details: private module details, private provider details

**Common Use Cases**:
- Finding internal organization modules
- Discovering custom providers
- Accessing proprietary infrastructure components

**Critical Parameters**:
- `terraform_org_name`: Organization name for private registry access
- `module_query`, `provider_query`: Search terms

## TypeScript Wrapper Architecture

### Client Architecture

**`scripts/client.ts`** provides the MCP connection manager:

```typescript
// Initialize MCP connection
await initializeMCPClient({
  command: "docker",
  args: ["run", "-i", "--rm", "-e", `TFE_TOKEN=${process.env.TFE_TOKEN}`, "hashicorp/terraform-mcp-server"]
});

// Call MCP tools
const result = await callMCPTool("toolName", { param: "value" });

// Clean up connection
await closeMCPClient();
```

### Tool Wrapper Pattern

Each tool wrapper follows this pattern:

```typescript
// Input/Output interfaces from JSON Schema
export interface CreateWorkspaceInput {
  workspace_name: string;
  terraform_org_name: string;
  auto_apply?: string;
  description?: string;
  // ...
}

export interface CreateWorkspaceOutput {
  content: Array<{ type: string; text: string }>;
  isError?: boolean;
}

// Type-safe wrapper function
export async function CreateWorkspace(input: CreateWorkspaceInput): Promise<CreateWorkspaceOutput> {
  return callMCPTool("CreateWorkspace", input);
}
```

**Benefits**:
- Full TypeScript type safety
- IDE autocomplete and IntelliSense
- Runtime type validation
- Clear input/output contracts

### Barrel Exports

Each category has an `index.ts` that re-exports all tools:

```typescript
// Import from category
import { CreateWorkspace, UpdateWorkspace, ListWorkspaces } from "./scripts/workspaces/index.js";

// Or import specific tool with types
import { CreateWorkspace, CreateWorkspaceInput, CreateWorkspaceOutput } from "./scripts/workspaces/createWorkspace.js";
```

## Common User Workflows

### Workflow 1: Setup New Environment

**User Intent**: "Create a new production environment for my API service"

**Guide to**:
1. Create workspace with appropriate settings
2. Set up variable sets for environment-specific config
3. Attach variable sets to workspace
4. Trigger initial plan

**Key Considerations**:
- Set `auto_apply: "false"` for production (manual approval)
- Use descriptive workspace names
- Tag workspaces for organization

### Workflow 2: Find and Use Registry Module

**User Intent**: "Find a good VPC module for AWS"

**Guide to**:
1. Search public registry for modules
2. Get module details and documentation
3. Review README and examples
4. Reference module in Terraform configuration

**Key Considerations**:
- Search with specific keywords (e.g., "vpc aws terraform-aws-modules")
- Check module version and compatibility
- Review provider requirements

### Workflow 3: Automate Deployments

**User Intent**: "Trigger deployments automatically when code changes"

**Guide to**:
1. Create runs programmatically
2. Monitor run status
3. Handle errors and failures
4. Implement retry logic if needed

**Key Considerations**:
- Use meaningful run messages
- Set appropriate run types (plan-and-apply vs plan-only)
- Monitor run status before proceeding

### Workflow 4: Manage Configuration at Scale

**User Intent**: "Update AWS region across 20 workspaces"

**Guide to**:
1. Create variable set with common configuration
2. Attach variable set to multiple workspaces
3. Update variables in variable set (propagates to all workspaces)

**Key Considerations**:
- Use variable sets for shared configuration
- Mark sensitive variables appropriately
- Test changes in non-production first

## Error Handling Patterns

### Standard Error Handling

```typescript
try {
  const result = await CreateWorkspace({
    workspace_name: "my-workspace",
    terraform_org_name: "my-org"
  });

  if (result.isError) {
    console.error("Workspace creation failed:", result.content);
    // Handle error
  } else {
    console.log("Workspace created successfully");
    // Continue workflow
  }
} catch (error) {
  console.error("MCP call failed:", error);
  // Handle connection/system error
}
```

### Common Error Scenarios

**Connection Errors**:
- Docker not running
- MCP server failed to start
- Network issues

**Authentication Errors**:
- Invalid or expired `TFE_TOKEN`
- Insufficient permissions for operation
- Token not set in environment

**API Errors**:
- Workspace already exists
- Organization not found
- Invalid parameter values

## Integration with Claude Code

### When to Use This Skill

Invoke this skill when users need to:
- Automate Terraform Cloud/Enterprise operations
- Programmatically manage workspaces
- Trigger runs from scripts or CI/CD
- Search registries for modules/providers
- Manage variables at scale

### When NOT to Use This Skill

Do NOT use this skill for:
- Direct Terraform CLI operations (use Terraform CLI directly)
- Local Terraform state management (this is Cloud/Enterprise only)
- Writing Terraform configurations (use terraform-style-guide instead)
- Writing Terraform tests (use terraform-test instead)
- Terraform Stacks configurations (use terraform-stacks instead)

### Skill Interaction with Other Skills

This skill complements other skills in the marketplace:

- **terraform-style-guide**: Use for writing Terraform configurations, then use this skill to deploy them
- **terraform-test**: Use for writing tests, then use this skill to trigger test runs in Cloud/Enterprise
- **terraform-stacks**: Use for Stacks configurations, then use this skill to manage Stack deployments programmatically

## Common User Questions

### "How do I authenticate?"

Set the `TFE_TOKEN` environment variable with a valid Terraform Cloud/Enterprise API token:

```bash
export TFE_TOKEN="your-token-here"
```

Get tokens from:
- **Terraform Cloud**: User Settings → Tokens
- **Terraform Enterprise**: User Settings → Tokens

### "Can I use this without Docker?"

The MCP server requires Docker. However, users could theoretically:
- Use the Terraform Cloud/Enterprise API directly (without MCP)
- Write their own API clients

But this skill is specifically designed for the HashiCorp MCP server approach.

### "How do I handle sensitive variables?"

Always set `sensitive: "true"` (string) when creating variables with secrets:

```typescript
await CreateWorkspaceVariable({
  workspace_name: "my-workspace",
  terraform_org_name: "my-org",
  key: "AWS_SECRET_ACCESS_KEY",
  value: process.env.AWS_SECRET,
  category: "env",
  sensitive: "true"  // String, not boolean!
});
```

### "Can I automate Terraform Enterprise on-premises?"

Yes! The MCP server supports both Terraform Cloud (SaaS) and Terraform Enterprise (on-premises). Use the same approach with your organization's Terraform Enterprise URL and API token.

### "What's the difference between workspace variables and variable sets?"

- **Workspace Variables**: Specific to one workspace
- **Variable Sets**: Shared across multiple workspaces (e.g., AWS credentials for all production workspaces)

Use variable sets for configuration shared across workspaces.

## Limitations and Constraints

### Not Suitable For

- Direct Terraform CLI operations (plan, apply, destroy locally)
- Local Terraform state management
- Terraform configuration generation (use language skills)
- Non-Terraform infrastructure management

### API Rate Limits

Terraform Cloud/Enterprise has API rate limits:
- Free tier: Lower limits
- Paid tiers: Higher limits
- Consider implementing retry logic with backoff

### Terraform Enterprise Compatibility

This skill works with both:
- **Terraform Cloud** (app.terraform.io)
- **Terraform Enterprise** (self-hosted)

Ensure your `TFE_TOKEN` matches your target environment.

## Testing and Troubleshooting

### Pre-Execution Checklist

Before using this skill, verify:

1. `TFE_TOKEN` is set: `echo $TFE_TOKEN`
2. Docker is running: `docker --version`
3. MCP server connectivity: `docker run -i --rm -e TFE_TOKEN=$TFE_TOKEN hashicorp/terraform-mcp-server`

### Common Issues

**"Connection refused"**:
- Check Docker is running
- Verify MCP server starts correctly
- Check network connectivity

**"Authentication failed"**:
- Verify `TFE_TOKEN` is set and valid
- Check token has required permissions
- Ensure token matches Terraform Cloud/Enterprise instance

**"Type errors"**:
- Use correct Input interface for each function
- Check string vs boolean types (e.g., `auto_apply: "true"` not `true`)
- Verify all required parameters are provided

## Version Information

- **Skill Version**: 1.0.0
- **Dependencies**: Docker, Node.js (optional for local TypeScript execution)
- **MCP Server**: hashicorp/terraform-mcp-server (Docker image)
- **Auto-Generated**: This skill was auto-generated by [mcp-to-claude-skill](https://github.com/hashi-demo-lab/mcp-to-claude-skill)

## Contributing to This Skill

When updating this skill:

1. **Keep wrapper functions in sync** - If MCP server API changes, regenerate wrappers
2. **Update documentation** - Ensure SKILL.md reflects current capabilities
3. **Test all examples** - Verify code examples work with current MCP server
4. **Maintain security guidelines** - Never include actual tokens in examples
5. **Keep type definitions accurate** - TypeScript interfaces should match JSON Schema

## References

- [Terraform Cloud API Documentation](https://developer.hashicorp.com/terraform/cloud-docs/api-docs)
- [Terraform Enterprise API](https://developer.hashicorp.com/terraform/enterprise/api-docs)
- [HashiCorp MCP Server](https://github.com/hashicorp/terraform-mcp-server)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
