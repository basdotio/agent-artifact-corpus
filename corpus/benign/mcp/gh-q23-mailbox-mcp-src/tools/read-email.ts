import { ImapClient } from "../imap-client";
import { ReadEmailSchema } from "../schemas/index";
import { resolveCredentials } from "../crypto";
import { escapeMd } from "../utils/markdown";
import type { TextContent } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

export async function handleReadEmail(
  imapClient: ImapClient,
  encryptionKey: string,
  input: z.infer<typeof ReadEmailSchema>
): Promise<{
  content: TextContent[];
}> {
  try {
    const creds = resolveCredentials(input.credentials!, encryptionKey);
    const email = await imapClient.readEmail(
      creds.user,
      creds.pass,
      input.folder,
      input.uid
    );

    const attachmentList =
      email.attachments.length > 0
        ? `\n### Attachments\n\n${email.attachments.map((a) => `- **${a.name}** (${(a.size / 1024).toFixed(2)} KB, ${a.type})`).join("\n")}`
        : "";
    const htmlNotice = email.hasHtmlAlternative
      ? "\n### HTML Alternative\n\nAn HTML version of this email was detected but is not rendered by mailbox-mcp for security reasons."
      : "";

    const markdown = `# Email Details

**From**: ${escapeMd(email.from)}
**To**: ${escapeMd(email.to)}
${email.cc ? `**CC**: ${escapeMd(email.cc)}\n` : ""}
${email.bcc ? `**BCC**: ${escapeMd(email.bcc)}\n` : ""}
**Subject**: ${escapeMd(email.subject)}
**Date**: ${email.date}
**Status**: ${email.read ? "Read" : "Unread"} ${email.flagged ? "| Flagged" : ""}
**UID**: ${input.uid}

---

## Body

${email.textBody || "(empty)"}

${htmlNotice}

${attachmentList}
`;

    return {
      content: [
        {
          type: "text",
          text: markdown,
        } as TextContent,
      ],
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [
        {
          type: "text",
          text: `Error reading email: ${errorMessage}`,
        } as TextContent,
      ],
    };
  }
}
