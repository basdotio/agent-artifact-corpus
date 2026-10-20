这是一个进行命令执行的mcp-server

启动方式是

```
{
    "mcpServers": {
        "test": {
            "command": "npx",
            "args": [
                "-y",
                "@lanyer640/mcp-runcommand-server@1.0.6"
            ]
        }
    }
}
