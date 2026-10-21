import { encrypt } from '../crypto';
import type { TextContent } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';

export const EncryptCredentialsSchema = z.object({
  imap_user: z.string().min(1).describe('IMAP email address'),
  imap_pass: z.string().min(1).describe('IMAP password or app-specific password'),
});

export function handleEncryptCredentials(
  encryptionKey: string,
  input: z.infer<typeof EncryptCredentialsSchema>
): {
  content: TextContent[];
} {
  try {
    const credentialJson = JSON.stringify({
      user: input.imap_user,
      pass: input.imap_pass,
    });

    const encrypted = encrypt(credentialJson, encryptionKey);

    const markdown = `# IMAP Credentials Encrypted

Your credentials have been securely encrypted using AES-256-GCM.

**Encrypted Token**:
\`\`\`
${encrypted}
\`\`\`

## How to Use

Copy the encrypted token above and pass it as the \`credentials\` parameter to mailbox tools:
- \`imap_list_folders\`
- \`imap_list_emails\`
- \`imap_search_emails\`
- \`imap_read_email\`
- \`smtp_send_email\`
- \`smtp_reply_email\`

Example:
\`\`\`json
{
  "credentials": "${encrypted}",
  "folder": "INBOX"
}
\`\`\`
**Security Note**: Keep this token secure — it grants access to your email account via the configured mailbox services.
You can safely reuse this token for multiple requests in this session.
`;

    return {
      content: [
        {
          type: 'text',
          text: markdown,
        } as TextContent,
      ],
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [
        {
          type: 'text',
          text: `Error encrypting credentials: ${errorMessage}`,
        } as TextContent,
      ],
    };
  }
}
