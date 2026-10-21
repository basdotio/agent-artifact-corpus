import { ImapClient } from "../imap-client";
import { ListEmailsSchema } from "../schemas/index";
import { resolveCredentials } from "../crypto";
import { escapeMd } from "../utils/markdown";
import type { TextContent } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

export async function handleListEmails(
  imapClient: ImapClient,
  encryptionKey: string,
  input: z.infer<typeof ListEmailsSchema>
): Promise<{
  content: TextContent[];
}> {
  try {
    const creds = resolveCredentials(input.credentials!, encryptionKey);
    const emails = await imapClient.listEmails(
      creds.user,
      creds.pass,
      input.folder,
      input.limit,
      input.offset,
      { since: input.since, before: input.before }
    );

    const markdown = `# Emails from ${input.folder}

**Showing**: ${input.offset + 1} to ${input.offset + emails.length} (limit: ${input.limit})
${input.since ? `**Since**: ${input.since}\n` : ""}${input.before ? `**Before**: ${input.before}\n` : ""}

${
  emails.length === 0
    ? "No emails found."
    : `
| UID | From | Subject | Date | Status |
|-----|------|---------|------|--------|
${emails.map((e) => `| ${e.uid} | ${escapeMd(e.from)} | ${escapeMd(e.subject)} | ${e.date} | ${e.read ? "Read" : "Unread"} |`).join("\n")}
`
}

**Total in folder**: ${emails.length > 0 ? "Multiple" : "0"} messages
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
          text: `Error listing emails: ${errorMessage}`,
        } as TextContent,
      ],
    };
  }
}
