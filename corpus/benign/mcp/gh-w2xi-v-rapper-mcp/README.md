# 🎤 v-rapper-mcp

A Model Context Protocol (MCP) server that provides access to Evan You's legendary v-rapper video from VueConf 2025! 🎵

## 📋 Prerequisites

- **Node.js 22+** is required

## ⚙️ Configuration

You can add the `v-rapper-mcp` in your MCP configuration:

```json
{
  "mcpServers": {
    "v-rapper-mcp": {
      "command": "npx",
      "args": ["v-rapper-mcp"]
    }
  }
}
```

## 📖 Usage

Once configured, you can use the `v-rapper` tool in your MCP client to get the video URL. Perfect for when you need some Vue.js inspiration with a beat! 🎶

## 🐛 Troubleshooting

- **Node.js version error**: Make sure you're using Node.js 22 or higher
- **MCP connection issues**: Ensure your MCP client is properly configured

## 📄 License

MIT - See [LICENSE](./LICENSE) for details

---

_Made with ❤️ for the Vue.js community_
