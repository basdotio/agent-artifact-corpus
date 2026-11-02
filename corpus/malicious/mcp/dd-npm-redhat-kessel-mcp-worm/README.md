# @redhat-cloud-services/hcc-kessel-mcp

An MCP (Model Context Protocol) server that provides live RBAC v1 → Kessel (v2) permission mappings for HCC frontend applications, sourced directly from the [rbac-config KSL schemas](https://github.com/RedHatInsights/rbac-config/tree/master/configs/prod/schemas/src).

## Tools

| Tool | Description |
|------|-------------|
| `listServices` | List all HCC services with Kessel permission schemas |
| `getServicePermissions` | Get all v1 → v2 mappings for a specific service |
| `getKesselPermission` | Look up the v2 relation for a v1 permission (supports wildcards) |
| `getMigrationExample` | Generate a `useSelfAccessCheck` code snippet for a v1 permission |

## Usage

### Claude Code (user-scoped)

```sh
claude mcp add --scope user hcc-rbac-kessel-local -- npx -y @redhat-cloud-services/hcc-kessel-mcp
```

### Claude Code (project-scoped)

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "hcc-rbac-kessel-local": {
      "command": "npx",
      "args": ["-y", "@redhat-cloud-services/hcc-kessel-mcp"]
    }
  }
}
```

## Examples

**Look up a v2 relation:**
> What's the v2 relation for `notifications:events:read`?

**Expand a wildcard:**
> What are all the v2 relations for `notifications:*:*`?

**Generate migration code:**
> Show me how to check for `advisor:recommendation_results:read` using the React Kessel SDK.

## License

Apache-2.0
