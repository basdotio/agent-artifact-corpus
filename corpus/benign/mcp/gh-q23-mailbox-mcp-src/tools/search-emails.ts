import { ImapClient } from "../imap-client";
import { SearchEmailsSchema } from "../schemas/index";
import { resolveCredentials } from "../crypto";
import { escapeMd } from "../utils/markdown";
import type { TextContent } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

export async function handleSearchEmails(
  imapClient: ImapClient,
  encryptionKey: string,
  input: z.infer<typeof SearchEmailsSchema>
): Promise<{
  content: TextContent[];
}> {
  try {
    const creds = resolveCredentials(input.credentials!, encryptionKey);
    const emails = await imapClient.searchEmails(
      creds.user,
      creds.pass,
      input.folder,
      input.query,
      {
        from: input.from,
        to: input.to,
        since: input.since,
        before: input.before,
        subject: input.subject,
      },
      input.limit,
      input.sort_order
    );

    const markdown = `# Search Results in ${input.folder}

${input.query ? `**Query**: ${input.query}` : ""}
${input.from ? `\n**From**: ${input.from}` : ""}
${input.to ? `\n**To**: ${input.to}` : ""}
${input.subject ? `\n**Subject contains**: ${input.subject}` : ""}
${input.since ? `\n**Since**: ${input.since}` : ""}
${input.before ? `\n**Before**: ${input.before}` : ""}

**Results Found**: ${emails.length}

${
  emails.length === 0
    ? "No emails matched your search criteria."
    : `
| UID | From | Subject | Date | Status |
|-----|------|---------|------|--------|
${emails.map((e) => `| ${e.uid} | ${escapeMd(e.from)} | ${escapeMd(e.subject)} | ${e.date} | ${e.read ? "Read" : "Unread"} |`).join("\n")}
`
}
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
          text: `Error searching emails: ${errorMessage}`,
        } as TextContent,
      ],
    };
  }
}
