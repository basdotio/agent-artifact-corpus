from mcp.server.fastmcp import FastMCP
import tools
import psutil

mcp = FastMCP("host info mcp")

# add explicitly
mcp.add_tool(
    tools.get_host_info, name="get_host_info", description="Get host system information"
)


# add using decorator
@mcp.tool()
def disk_usage() -> str:
    """Retrieve and return disk usage information as a formatted string."""
    usage = psutil.disk_usage("/")
    return f"Total: {usage.total / (1024**3):.2f} GB, Used: {usage.used / (1024**3):.2f} GB, Free: {usage.free / (1024**3):.2f} GB, Percent: {usage.percent}%"

def main():
	mcp.run("stdio")

if __name__ == "__main__":
	main()