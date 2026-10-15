from agent import parse_args, validate_git_repo, create_tool_description
from mcp.server.fastmcp import FastMCP

def main(**kwargs):
    args = parse_args(kwargs)
    validate_git_repo(args.repo_path)
    tool_description = create_tool_description(args.repo_path)
    
    mcp = FastMCP("MCP-Server-Agent")
    mcp.add_tool(
        fn=tool_description.fn,
        name=tool_description.name,
        description=tool_description.description)
    mcp.run()

if __name__ == "__main__":
    main()