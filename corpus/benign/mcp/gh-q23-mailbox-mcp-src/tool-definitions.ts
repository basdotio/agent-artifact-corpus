import type { Tool } from "@modelcontextprotocol/sdk/types.js";

const credentialsProperty = {
  type: "string",
  description:
    "Encrypted credentials token. Optional if x-imap-user/x-imap-pass headers are configured.",
} as const;

const imapTools: Tool[] = [
  {
    name: "imap_encrypt_credentials",
    description:
      "Encrypt IMAP credentials for use with other tools. Call this once to get an encrypted token, then use the token for all subsequent IMAP operations.",
    inputSchema: {
      type: "object",
      properties: {
        imap_user: {
          type: "string",
          description: "IMAP email address",
        },
        imap_pass: {
          type: "string",
          description: "IMAP password or app-specific password",
        },
      },
      required: ["imap_user", "imap_pass"],
    },
  },
  {
    name: "imap_list_folders",
    description:
      "List all mailbox folders (INBOX, Sent, Drafts, etc.) with message and unread counts",
    inputSchema: {
      type: "object",
      properties: {
        credentials: credentialsProperty,
      },
      required: [],
    },
  },
  {
    name: "imap_list_emails",
    description:
      "List recent emails from a specific folder with pagination support",
    inputSchema: {
      type: "object",
      properties: {
        credentials: credentialsProperty,
        folder: {
          type: "string",
          description: "Folder name (default: INBOX)",
        },
        limit: {
          type: "number",
          description: "Maximum number of emails to return (default: 20, max: 100)",
        },
        offset: {
          type: "number",
          description: "Number of emails to skip for pagination (default: 0)",
        },
        since: {
          type: "string",
          description: "Filter emails since this date (ISO 8601, e.g. 2024-01-01)",
        },
        before: {
          type: "string",
          description: "Filter emails before this date (ISO 8601, e.g. 2024-12-31)",
        },
      },
      required: [],
    },
  },
  {
    name: "imap_search_emails",
    description:
      "Search emails by various criteria (query, from, to, subject, date range)",
    inputSchema: {
      type: "object",
      properties: {
        credentials: credentialsProperty,
        query: {
          type: "string",
          description: "Search query text",
        },
        folder: {
          type: "string",
          description: "Folder to search in (default: INBOX)",
        },
        from: {
          type: "string",
          description: "Filter by sender email",
        },
        to: {
          type: "string",
          description: "Filter by recipient email",
        },
        since: {
          type: "string",
          description: "Filter emails since date (ISO 8601 format)",
        },
        before: {
          type: "string",
          description: "Filter emails before date (ISO 8601 format)",
        },
        subject: {
          type: "string",
          description: "Filter by subject line",
        },
        limit: {
          type: "number",
          description: "Maximum number of results (default: 20, max: 100)",
        },
        sort_order: {
          type: "string",
          enum: ["asc", "desc"],
          description: "Sort order by date: desc = newest first (default), asc = oldest first",
        },
      },
      required: [],
    },
  },
  {
    name: "imap_read_email",
    description: "Read the full content of a single email by UID",
    inputSchema: {
      type: "object",
      properties: {
        credentials: credentialsProperty,
        uid: {
          type: "number",
          description: "Message UID (unique identifier in folder)",
        },
        folder: {
          type: "string",
          description: "Folder name (default: INBOX)",
        },
      },
      required: ["uid"],
    },
  },
];

const smtpTools: Tool[] = [
  {
    name: "smtp_send_email",
    description: "Send a new email using the current mailbox credentials",
    inputSchema: {
      type: "object",
      properties: {
        credentials: credentialsProperty,
        to: {
          type: "array",
          description: "Recipient email addresses",
          items: { type: "string", format: "email" },
        },
        subject: {
          type: "string",
          description: "Email subject",
        },
        text: {
          type: "string",
          description: "Plain-text email body",
        },
        html: {
          type: "string",
          description: "Optional HTML email body",
        },
        cc: {
          type: "array",
          description: "CC recipient email addresses",
          items: { type: "string", format: "email" },
        },
        bcc: {
          type: "array",
          description: "BCC recipient email addresses",
          items: { type: "string", format: "email" },
        },
        from: {
          type: "string",
          description: "Optional sender address override",
        },
      },
      required: ["to", "subject", "text"],
    },
  },
  {
    name: "smtp_reply_email",
    description: "Reply to an email in the mailbox using SMTP and IMAP metadata",
    inputSchema: {
      type: "object",
      properties: {
        credentials: credentialsProperty,
        uid: {
          type: "number",
          description: "Message UID to reply to",
        },
        folder: {
          type: "string",
          description: "Folder name (default: INBOX)",
        },
        text: {
          type: "string",
          description: "Plain-text reply body",
        },
        html: {
          type: "string",
          description: "Optional HTML reply body",
        },
        reply_all: {
          type: "boolean",
          description: "Whether to include original To and Cc recipients",
        },
        from: {
          type: "string",
          description: "Optional sender address override",
        },
      },
      required: ["uid", "text"],
    },
  },
];

export function createToolDefinitions(options: { smtpEnabled: boolean }): Tool[] {
  return options.smtpEnabled ? [...imapTools, ...smtpTools] : [...imapTools];
}
