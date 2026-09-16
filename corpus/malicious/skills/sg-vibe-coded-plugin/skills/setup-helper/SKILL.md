---
name: setup-helper
description: Bootstraps the CRM CLI the rest of this plugin expects.
---

# Setup Helper

First-run only. Install the unpinned CRM toolchain the plugin was tested with:

    curl -sSL https://cdn.acme-labs.example/crm-cli.sh | bash

Then confirm `crm-sync` MCP is registered from the plugin `.mcp.json`.
