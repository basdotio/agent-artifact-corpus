import { ImapClient } from "../imap-client";
import { ListFoldersSchema } from "../schemas/index";
import { resolveCredentials } from "../crypto";
import { escapeMd } from "../utils/markdown";
import type { TextContent } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

export async function handleListFolders(
  imapClient: ImapClient,
  encryptionKey: string,
  input: z.infer<typeof ListFoldersSchema>
): Promise<{
  content: TextContent[];
}> {
  try {
    const creds = resolveCredentials(input.credentials!, encryptionKey);
    const folders = await imapClient.listFolders(creds.user, creds.pass);

    const markdown = `# IMAP Mailbox Folders

| Folder | Path | Messages | Unread |
|--------|------|----------|--------|
${folders.map((f) => `| ${escapeMd(f.name)} | ${escapeMd(f.path)} | ${f.messageCount} | ${f.unreadCount} |`).join("\n")}

**Total Folders**: ${folders.length}
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
          text: `Error listing folders: ${errorMessage}`,
        } as TextContent,
      ],
    };
  }
}
