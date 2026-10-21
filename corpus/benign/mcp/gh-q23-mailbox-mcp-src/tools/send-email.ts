import type { TextContent } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { resolveCredentials } from "../crypto";
import { SendEmailSchema } from "../schemas";
import { SmtpClient } from "../smtp-client";
import { resolveSenderAddress } from "../smtp-utils";
import { escapeMd } from "../utils/markdown";

export async function handleSendEmail(
  smtpClient: SmtpClient,
  encryptionKey: string,
  input: z.infer<typeof SendEmailSchema>
): Promise<{
  content: TextContent[];
}> {
  try {
    const creds = resolveCredentials(input.credentials!, encryptionKey);
    const from = resolveSenderAddress(input.from, creds.user);
    const result = await smtpClient.sendEmail(creds.user, creds.pass, {
      from,
      to: input.to,
      cc: input.cc,
      bcc: input.bcc,
      subject: input.subject,
      text: input.text,
      html: input.html,
    });

    const markdown = `# Email Sent

**From**: ${escapeMd(from)}
**To**: ${escapeMd(input.to.join(", "))}
${input.cc && input.cc.length > 0 ? `**CC**: ${escapeMd(input.cc.join(", "))}\n` : ""}${input.bcc && input.bcc.length > 0 ? `**BCC**: ${escapeMd(input.bcc.join(", "))}\n` : ""}**Subject**: ${escapeMd(input.subject)}
**Message ID**: ${result.messageId || "(not provided)"}
**Accepted**: ${result.accepted.length > 0 ? result.accepted.join(", ") : "none"}
${result.rejected.length > 0 ? `**Rejected**: ${result.rejected.join(", ")}` : ""}
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
          text: `Error sending email: ${errorMessage}`,
        } as TextContent,
      ],
    };
  }
}
