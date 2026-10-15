# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""The base of the server's structured data: tool arguments, results and journal entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """A record with a schema agents can read.

    Each field's docstring becomes its description in the schema. Unknown fields are
    refused, so a misspelt argument fails loudly instead of being ignored.
    """

    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")
