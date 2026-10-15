# ReachDirect-MCP

A local Model Context Protocol (MCP) tool, for Agentic Workflow that automates personalized cold outreach through Brevo Transactional Email and WhatsApp Web. Built specifically for Small Companies and Startups to run completely locally and privately.

ReachDirect connects your AI assistant directly to your communication channels. It autonomously sends highly personalized emails via the Brevo v3 API, dispatches automated WhatsApp messages using local browser automation (bypassing strict bot detections), and automatically logs every contact outreach into a central Excel tracking file on your Desktop.

---

## 🛠️ Prerequisites

Before installing, you need a few basic tools installed on your computer:

1. **Python (3.10+)** — The programming language this runs on.
2. **Git for Windows/Mac** — Used to download this repository.
3. **An MCP-Compatible AI Client** — You need an AI to command the tool. Choose one:
   * [Claude Desktop](https://claude.ai/download) (Recommended for ease of use)
   * Cursor IDE (For developers)
   * Antigravity CLI (For local terminal users)

---

## 🚀 Quick Start Guide

Open your terminal (**Command Prompt** or **PowerShell** on Windows, or **Terminal** on Mac/Linux) and run these commands:

```bash
git clone https://github.com/netizen4-bit/reach_direct-mcp
cd reach_direct-mcp
pip install -r requirements.txt
playwright install
```

---

## 🔗 Connecting to your AI (MCP Client Configuration)

To let your AI use this tool, you must tell it where this folder is located on your computer and provide your Brevo API key.

Add ReachDirect to your MCP client configuration file (e.g., `claude_desktop_config.json`):

⚠️ **IMPORTANT:** You MUST replace the `args` path below with the exact location where you downloaded this folder on your computer. You must also add your Brevo API key to the `env` section.

```json
{
  "mcpServers": {
    "reachdirect": {
      "command": "python",
      "args": ["C:\\YOUR\\EXACT\\PATH\\HERE\\reach_direct-mcp\\reach_direct.py"],
      "env": {
        "BREVO_API_KEY": "xkeysib-your-brevo-api-key-here"
      }
    }
  }
}
```

* *(Example for Windows: `"C:\\Users\\YOUR_NAME\\Documents\\reach_direct-mcp\\reach_direct.py"`)*
* *(Example for Mac/Linux: `"/Users/YOUR_NAME/Documents/reach_direct-mcp/reach_direct.py"`)*

---

## 📁 Project Structure

```text
reach_direct-mcp/
├── reach_direct.py       # The core Bridge & Agent tools. Connects to your AI client.
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## 🧰 Tools Reference & Prompting

### 🧠 How to Structure High-Converting Outreach Prompts

Because ReachDirect operates autonomously, the quality of your outreach depends on clear instructions:

1. **Tool #1 (`send_email`)**: Uses the Brevo v3 API to send emails. Make sure your sending domain is authenticated in Brevo (SPF/DKIM) or your emails will fail.
2. **Tool #2 (`send_whatsapp`)**: Uses local browser automation to send WhatsApp messages. The first time you run this, it will generate an auto-refreshing `WhatsApp_Login.html` file on your desktop. Open it and scan the QR code to log in.
3. **Tool #3 (`save_outreach_contact`)**: Automatically saves the details of the person you just contacted to an `outreach_contacts.xlsx` file on your Desktop.

**The Chained Prompt Formula:**

> "I need to reach out to John Doe regarding our new product.
> 
> Step 1: Use your `send_email` tool to send an email to john.doe@example.com from my.email@company.com with a polite introduction.
> 
> Step 2: Use your `send_whatsapp` tool to send a quick follow-up message to +1234567890 letting him know I sent an email.
> 
> Step 3: Use your `save_outreach_contact` tool to log John Doe into my outreach tracker."

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## ☕ Support the Developer

If this tool saved you a day, and if you use my other open-source workflow tools, consider supporting the development. Your backing helps keep these small AI tools projects completely free.

[![Patreon](https://img.shields.io/badge/PATREON-SUPPORT%20ME-F96854?style=for-the-badge&logo=patreon&logoColor=white&labelColor=555555)](https://patreon.com/netizen4_bit)
