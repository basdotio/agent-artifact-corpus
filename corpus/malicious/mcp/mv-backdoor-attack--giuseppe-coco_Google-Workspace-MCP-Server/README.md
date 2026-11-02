# Google Workspace MCP Server

A Model Context Protocol (MCP) server that acts as a secure bridge between your personal Google Workspace account (Gmail, Calendar, etc.) and any MCP-compatible AI client, such as Claude Desktop.

## Features

*   **Google Calendar**:
    *   Effortlessly list and search for events on your primary calendar within a specific date range.
    *   Create new events with detailed information like title, description, start, and end times.
    *   Update existing events, allowing for partial modifications such as changing the title or time.
    *   Delete events directly from your calendar.
*   **Gmail**:
    *   Read the content of your most recent email to stay up-to-date.
    *   Search for specific emails by their subject line to find important conversations.
    *   Compose and send new emails directly from your account.
*   **Google Drive**:
    *   Search for files and folders using powerful query strings.
    *   Create new Google Docs with a specified title and initial content.
    *   Update the entire content of an existing Google Doc.
    *   Manage your files by moving them to the bin or deleting them permanently.

## Getting Started

Follow these steps to set up the server and run the example AI agent.

### Prerequisites

*   Python 3.9+ and `uv` (or `pip`).
*   A Google Cloud project with the necessary APIs enabled.
*   Claude Desktop.

### Step 1: Configure your Google Cloud Project

You need to authorize this application to access your Google data. This is a one-time setup.

1.  **Go to the Google Cloud Console**: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2.  **Create a new project** (or use an existing one).
3.  **Enable APIs**:
    *   Go to "APIs & Services" -> "Library".
    *   Search for and **Enable** the **Gmail API**.
    *   Search for and **Enable** the **Google Calendar API**.
    *   Search for and **Enable** the **Google Drive API**.
4.  **Create OAuth Credentials**:
    *   Go to "APIs & Services" -> "Credentials".
    *   Click "Create Credentials" -> "OAuth client ID".
    *   If prompted, configure the "OAuth consent screen". Choose **External** and provide a name for the app. You can skip most other fields for personal use. Add your Google account email as a Test User.
    *   For "Application type", select **Desktop app**.
    *   Give it a name (e.g., "GSuite MCP Client").
5.  **Download Credentials**:
    *   After creating the client ID, click the "Download JSON" icon.
    *   Rename the downloaded file to `client_secrets.json` and place it in the **root directory of this project**.

### Step 2: Install Dependencies

Clone this repository and install the required Python packages for both the server and the client.

```bash
git clone <your-repo-url>
cd <your-repo-name>
uv venv # Create a virtual environment
source .venv/bin/activate # On Windows: .venv\Scripts\activate
# Install server dependencies
uv install -r requirements.txt
```

### Step 3: Run the One-Time Authorization

Before you can run the server, you need to authorize it with your Google account. Run the `get_credentials.py` script from your terminal:

```bash
python get_credentials.py
```

*   This will open a browser window.
*   Log in with your Google account and grant the requested permissions.
*   After you approve, the script will automatically create a `token.json` file in the project directory. This file stores your authorization tokens so you don't have to log in every time.

### Step 4: Set Up and Run the AI Agent Client

As an example, I'll show you how to configure Claude Desktop as an MCP Client. However, you can use whatever MCP Client available on Internet.

1.  **Configure Claude Desktop**:
    
    (Windows) Open `C:\Users\<user>\AppData\Roaming\Claude\claude_desktop_config.json` and add 
    ```json
    {
        "mcpServers": {
            "GsuiteMCPServer": {
                "command": "absolute-path-to-your-python-executable-in-virtual-environment",
                "args": [
                    "<mcp_server.py-abs-path>"
                ]
            }
        }
    }   
    ```

2.  **Use the available tools**:
    Ask Claude something like:
    
    - Create a Google Calendar Event based on the content of the last mail being sent to my inbox.
      If you cannot create an event, create a sort of 'reminder event' in order to remind me to check that email.
    
    - Create a Google Docs drafting a trip plan in San Francisco.
    
    - Check what are my availabilities next week for a two-hours call with a customer.

    - Edit the start time of the meeting with the VCs to 10 A.M.

    - Search for new e-mails in my inbox talking about AI news.

    - Send an email to my supplier telling him he's late and I need the next lot as soon as possible.

    - Much more.


## Roadmap & Future Plans

This server is the foundation for a much larger vision. The goal is to provide a comprehensive MCP server for the entire Google Workspace suite. Future additions will include tools for:

*   📝 **Google Docs**: More granular document manipulation, such as appending text or reading specific sections instead of overwriting the whole file.
*   📊 **Google Sheets**: Read data from sheets, append new rows, update cells, and even perform calculations.
*   📨 New functionalities for **Gmail**.
*   📅 New functionalities for **Google Calendar**.
*   🗂️ New functionalities for **Google Drive**.

Contributions are welcome!

## Contributing

If you'd like to contribute, please feel free to fork the repository and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
