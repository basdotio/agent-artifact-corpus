from typing import Literal

# What a tool does, as the Hub decides it (ADR 0002), never as its server claims.
Access = Literal["read", "write"]
