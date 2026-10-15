"""Wire error codes shared with the Go client (localoctop/errors.go).

Codes >= 4000 are localoctop-bridge domain errors; negative codes follow
JSON-RPC 2.0 conventions. Both sides must agree on these values so an
error raised on the employee machine is rendered correctly inside Octop.
"""

CODE_OK = 0
CODE_INVALID_PARAMS = -32602
CODE_METHOD_NOT_FOUND = -32601
CODE_PARSE_ERROR = -32700
CODE_INTERNAL = -32000

CODE_NOT_ALLOWED = 4001      # path outside whitelist / traversal / symlink escape
CODE_NOT_FOUND = 4002        # file or directory does not exist
CODE_TOO_LARGE = 4003        # payload exceeds configured size limit
CODE_WRITE_DISABLED = 4004   # write tool while AllowWrite=false
CODE_TIMEOUT = 4005          # operation exceeded request timeout

CODE_NO_BRIDGE = 4101        # no bridge session registered for this user
CODE_AUTH_FAILED = 4102      # bad or missing token
CODE_MCP_UNPAIRED = 4103     # v0.6.1: mcp token has no paired bridge token

CODE_DESCRIPTIONS = {
    CODE_INVALID_PARAMS: "invalid params",
    CODE_METHOD_NOT_FOUND: "method not found",
    CODE_PARSE_ERROR: "parse error",
    CODE_INTERNAL: "internal error",
    CODE_NOT_ALLOWED: "path not allowed",
    CODE_NOT_FOUND: "not found",
    CODE_TOO_LARGE: "payload too large",
    CODE_WRITE_DISABLED: "write disabled",
    CODE_TIMEOUT: "timeout",
    CODE_NO_BRIDGE: "no bridge connected",
    CODE_AUTH_FAILED: "authentication failed",
    CODE_MCP_UNPAIRED: "mcp token not paired",
}


class BridgeProtocolError(Exception):
    """A structured error that maps 1:1 onto a JSON-RPC error object."""

    def __init__(self, code: int, message: str | None = None):
        super().__init__(message or CODE_DESCRIPTIONS.get(code, f"error {code}"))
        self.code = code
        self.message = message or CODE_DESCRIPTIONS.get(code, f"error {code}")

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}
