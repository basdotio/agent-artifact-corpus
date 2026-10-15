from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from get_user import router as user_router
from user_signup import router as signup_router
from mcp_server import mcp

# Initialize the FastAPI app
app = FastAPI()

app.include_router(user_router, prefix="/users")
app.include_router(signup_router, prefix="/auth", tags=["Auth"])

# Mount FastMCP server (HTTP DB management routes at /mcp/db/... and MCP protocol at /mcp/mcp)
app.mount("/mcp", mcp.http_app())

# Convenience redirect so visiting /signup opens /auth/signup
@app.get("/signup", include_in_schema=False)
def redirect_signup():
    return RedirectResponse(url="/auth/signup")


