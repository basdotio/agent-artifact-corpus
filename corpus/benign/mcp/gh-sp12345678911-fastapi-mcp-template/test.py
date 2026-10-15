from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
import uvicorn

app = FastAPI()


@app.get("/")
def read_root():
    '''
        return {"Hello": "World"} function
        Args:
            None
        Returns:
            dict: A dictionary with a greeting message
    '''
    return {"Hello": "World"}

# Auto-generated operation_id (something like "read_user_users__user_id__get")
@app.get("/users/{user_id}")
async def read_user(user_id: int, operation_id="get_user"):
    '''
        Returns:
            dict: A dictionary with a greeting message
    '''
    return {"user_id": user_id}

# # Explicit operation_id (tool will be named "get_user_info")
# @app.get("/users/{user_id}", operation_id="get_user_info")
# async def get_user_info(user_id: int):
#     return {"user_id": user_id}

mcp = FastApiMCP(
    app,
    # base_url="http://localhost:8000",
    # Optional parameters
    name="My API MCP",
    description="My API description",
    # include_operations=["get_user"]
    # base_url="http://localhost:8000",
)


# Mount the MCP server directly to your FastAPI app
mcp.mount()

# 添加啟動伺服器的代碼
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)