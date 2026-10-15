# Brightspace MCP Server

A Model Context Protocol (MCP) server that allows you to access your Purdue University Brightspace account through Claude Desktop. Ask Claude about your courses, assignments, and grades in natural language!

## Overview

Since students can't access the official D2L Brightspace API, this project uses Playwright for web scraping to extract Brightspace data. It handles Duo Mobile 2FA authentication and integrates seamlessly with Claude Desktop through the Model Context Protocol.

<img src="img/architecture.png" alt="Architecture Diagram" width="600">

## Features

- ✅ **Automated Duo Mobile 2FA** - Handles Purdue's two-factor authentication
- ✅ **Course List Extraction** - Get all your enrolled courses
- ✅ **MCP Integration** - Works with Claude Desktop for natural language queries
- ✅ **Secure Credentials** - Environment-based credential management
- 🟡 **Assignment Scraping** - In development
- 🟡 **Grade Tracking** - Planned feature

## Prerequisites

- **Python 3.12** (required for compatibility)
- **macOS** (tested on macOS, may work on other platforms)
- **Purdue Career Account** with Brightspace access
- **Duo Mobile** app configured for your account
- **Claude Desktop** installed ([Download here](https://claude.ai/download))

## Installation

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-username/brightspace-mcp-server.git
cd brightspace-mcp-server

# Run the automated setup script
# This creates a virtual environment with Python 3.12 and installs all dependencies
python3 setup.py

# Activate the virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### Step 2: Configure Credentials

Create a `.env` file in the project root:

```bash
PURDUE_USERNAME=your_purdue_username
PURDUE_PASSWORD=your_purdue_password
```

**⚠️ Important:** Never commit your `.env` file to git! It's already in `.gitignore`.

### Step 3: Test the Scraper (Optional)

Before setting up Claude Desktop, you can test if the scraper works:

```bash
# Test basic connectivity and authentication
python testing/playwright_trial.py

# Test full course scraping
python brightspace_api.py
```

This will:
1. Open a browser window
2. Navigate to Purdue Brightspace
3. Prompt you to approve Duo Mobile authentication
4. Scrape your course list
5. Save data to `brightspace_data.json`

### Step 4: Configure Claude Desktop

1. **Open Claude Desktop**
2. **Go to**: `File` → `Settings` → `Developer`
3. **Click**: `Edit Config`
4. **Add this configuration** to the opened file:

```json
{
  "mcpServers": {
    "brightspace": {
      "command": "/absolute/path/to/brightspace-mcp-server/venv/bin/python",
      "args": [
        "/absolute/path/to/brightspace-mcp-server/mcp_server.py"
      ]
    }
  }
}
```

**⚠️ Important:** Replace `/absolute/path/to/` with your actual project path. For example:
```
/Users/yourname/Documents/brightspace-mcp-server/venv/bin/python
```

To get your absolute path, run this in the project directory:
```bash
pwd
```

5. **Save** the configuration file
6. **Restart** Claude Desktop completely

### Step 5: Test the Integration

Open Claude Desktop and try these commands:

```
"What tools do you have available?"
"Can you use the hello tool?"
```

If you see the `hello` tool, the integration is working! 🎉

## Project Structure

```
brightspace-mcp-server/
├── brightspace_api.py          # Core Brightspace scraper
├── mcp_server.py               # MCP server for Claude Desktop
├── testing/
│   └── playwright_trial.py     # Authentication test script
├── setup.py                    # Automated setup script
├── requirements.txt            # Python dependencies
├── .env                        # Your credentials (create this)
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## How It Works

### Authentication Flow

```
Brightspace Login Page
         ↓
Click "Purdue West Lafayette / Indianapolis"
         ↓
Enter Username & Password
         ↓
Approve Duo Mobile 2FA on Your Phone
         ↓
Authenticated Session Established
         ↓
MCP Server Can Now Access Your Data
```

### MCP Integration

```
You: "What courses am I taking?"
         ↓
Claude Desktop → MCP Server → Brightspace Scraper → Your Courses
         ↓
Claude: "You're enrolled in CS 47100, CS 47500, COM 21700..."
```

## Available MCP Tools

Once configured, you can ask Claude to:

- **`hello`** - Test that the MCP server is working
- More tools coming soon (get_courses, get_assignments, etc.)

## Troubleshooting

### MCP Server Not Showing in Claude

1. **Verify paths are absolute** in `claude_desktop_config.json`
2. **Check Python version**: Must be Python 3.12 (`python --version`)
3. **Restart Claude Desktop** completely
4. **Check Claude Desktop logs**: `~/Library/Logs/Claude/main.log`

### Authentication Fails

1. **Check credentials** in `.env` file
2. **Test manually**: Run `python testing/playwright_trial.py`
3. **Approve Duo Mobile** quickly when prompted (60-second timeout)
4. **Check network connection** to Purdue servers

### No Courses Found

1. **Run the scraper directly**: `python brightspace_api.py`
2. **Check the debug screenshot**: `homepage_debug.png`
3. **Verify you're enrolled** in courses on Brightspace
4. **CSS selectors may have changed** - open an issue if this happens

## Development

### Testing the Scraper

```bash
# Activate virtual environment
source venv/bin/activate

# Test authentication
python testing/playwright_trial.py

# Test course scraping
python brightspace_api.py
```

### Modifying the MCP Server

The MCP server is in `mcp_server.py`. To add new tools:

1. Add tool definition in `@app.list_tools()`
2. Add tool handler in `@app.call_tool()`
3. Implement scraper method in `brightspace_api.py`
4. Restart Claude Desktop

## Important Notes

- **Terms of Service**: This project respects Purdue's terms of service and only accesses your own data
- **Rate Limiting**: Uses reasonable scraping intervals to avoid server load
- **Security**: Credentials are stored locally in `.env` and never committed to git
- **Maintenance**: CSS selectors may need updates if Brightspace changes their UI

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

## License

See [LICENSE](LICENSE) file for details.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Open an issue on GitHub
3. Contact Purdue IT if you have Brightspace access issues

## Acknowledgments

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Model Context Protocol
- [Claude Desktop](https://claude.ai/download) - AI assistant integration

---

**Note:** This is an unofficial project and is not affiliated with Purdue University or D2L Corporation.