import { z } from "zod";

// Shared credentials field for all tools — optional when x-imap-user/x-imap-pass headers are set
const credentialsField = z.string().optional().describe(
  "Base64-encoded encrypted IMAP credentials (use imap_encrypt_credentials tool to generate). " +
  "Optional if x-imap-user and x-imap-pass headers are configured in the MCP connector settings."
);

const emailArrayField = (
  description: string,
  minimum = 0
): z.ZodArray<z.ZodString, "many"> =>
  z.array(z.string().email()).min(minimum).describe(description);

const isoDateField = (
  description: string
): z.ZodType<string | undefined> =>
  z.string().optional().refine(
    (val) => val === undefined || !isNaN(new Date(val).getTime()),
    { message: "Must be a valid date string (e.g. 2024-01-01)" }
  ).describe(description);

export const ListFoldersSchema = z.object({
  credentials: credentialsField,
});

export const ListEmailsSchema = z.object({
  credentials: credentialsField,
  folder: z.string().max(200).regex(/^[^\r\n]*$/, "Folder name must not contain newlines").optional().default("INBOX"),
  limit: z.number().int().min(1).max(100).optional().default(20),
  offset: z.number().int().min(0).optional().default(0),
  since: isoDateField("Filter emails since this date (ISO 8601 or YYYY-MM-DD)"),
  before: isoDateField("Filter emails before this date (ISO 8601 or YYYY-MM-DD)"),
});

export const SearchEmailsSchema = z.object({
  credentials: credentialsField,
  query: z.string().optional(),
  folder: z.string().max(200).regex(/^[^\r\n]*$/, "Folder name must not contain newlines").optional().default("INBOX"),
  from: z.string().optional(),
  to: z.string().optional(),
  since: isoDateField("Filter emails since this date (ISO 8601 or YYYY-MM-DD)"),
  before: isoDateField("Filter emails before this date (ISO 8601 or YYYY-MM-DD)"),
  subject: z.string().optional(),
  limit: z.number().int().min(1).max(100).optional().default(20),
  sort_order: z.enum(["asc", "desc"]).optional().default("desc"),
});

export const ReadEmailSchema = z.object({
  credentials: credentialsField,
  uid: z.number().int().positive(),
  folder: z.string().max(200).regex(/^[^\r\n]*$/, "Folder name must not contain newlines").optional().default("INBOX"),
});

export const SendEmailSchema = z.object({
  credentials: credentialsField,
  to: emailArrayField("Recipient email addresses", 1),
  subject: z.string().min(1),
  text: z.string().min(1),
  html: z.string().optional(),
  cc: emailArrayField("CC recipient email addresses").optional(),
  bcc: emailArrayField("BCC recipient email addresses").optional(),
  from: z.string().email().optional(),
});

export const ReplyEmailSchema = z.object({
  credentials: credentialsField,
  uid: z.number().int().positive(),
  folder: z.string().max(200).regex(/^[^\r\n]*$/, "Folder name must not contain newlines").optional().default("INBOX"),
  text: z.string().min(1),
  html: z.string().optional(),
  reply_all: z.boolean().optional().default(false),
  from: z.string().email().optional(),
});

export type ListFoldersInput = z.infer<typeof ListFoldersSchema>;
export type ListEmailsInput = z.infer<typeof ListEmailsSchema>;
export type SearchEmailsInput = z.infer<typeof SearchEmailsSchema>;
export type ReadEmailInput = z.infer<typeof ReadEmailSchema>;
export type SendEmailInput = z.infer<typeof SendEmailSchema>;
export type ReplyEmailInput = z.infer<typeof ReplyEmailSchema>;
