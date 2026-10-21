import type { TextContent } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { resolveCredentials } from "../crypto";
import { ImapClient } from "../imap-client";
import { ReplyEmailSchema } from "../schemas";
import { SmtpClient } from "../smtp-client";
import {
  buildReplyRecipients,
  buildReplyThreadHeaders,
  normalizeReplySubject,
  resolveSenderAddress,
} from "../smtp-utils";
import { escapeMd } from "../utils/markdown";

export async function handleReplyEmail(
  imapClient: ImapClient,
  smtpClient: SmtpClient,
  encryptionKey: string,
  input: z.infer<typeof ReplyEmailSchema>
): Promise<{
  content: TextContent[];
}> {
  try {
    const creds = resolveCredentials(input.credentials!, encryptionKey);
    const context = await imapClient.getReplyContext(
      creds.user,
      creds.pass,
      input.folder,
      input.uid
    );
    const recipients = buildReplyRecipients(
      context,
      creds.user,
      input.reply_all
    );
    const headers = buildReplyThreadHeaders(context);
    const from = resolveSenderAddress(input.from, creds.user);
    const subject = normalizeReplySubject(context.subject);

    const result = await smtpClient.sendEmail(creds.user, creds.pass, {
      from,
      to: recipients.to,
      cc: recipients.cc.length > 0 ? recipients.cc : undefined,
      subject,
      text: input.text,
      html: input.html,
      inReplyTo: headers.inReplyTo,
      references: headers.references,
    });

    const markdown = `# Reply Sent

**Replying To UID**: ${input.uid}
**From**: ${escapeMd(from)}
**To**: ${escapeMd(recipients.to.join(", "))}
${recipients.cc.length > 0 ? `**CC**: ${escapeMd(recipients.cc.join(", "))}\n` : ""}**Subject**: ${escapeMd(subject)}
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
          text: `Error replying to email: ${errorMessage}`,
        } as TextContent,
      ],
    };
  }
}
