# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""avenir-mcp — an MCP server for YNAB, built for agents."""

__version__ = "0.6.0"

# The version of YNAB's API this release is built and tested against. It must match
# the snapshot in api/ynab-operations.json, which the weekly "YNAB API drift" check
# compares with the live specification; a test enforces the match.
YNAB_API_VERSION = "1.87.0"
