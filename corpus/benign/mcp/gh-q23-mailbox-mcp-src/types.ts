export interface ImapConfig {
  host: string;
  port: number;
  tls: boolean;
}

export interface SmtpConfig {
  host: string;
  port: number;
  tls: boolean;
}

export interface MailboxInfo {
  name: string;
  path: string;
  messageCount: number;
  unreadCount: number;
  flags?: string[];
}

export interface EmailListItem {
  uid: number;
  subject: string;
  from: string;
  to: string;
  date: string;
  read: boolean;
  flagged: boolean;
  messageId?: string;
}

export interface EmailContent {
  uid: number;
  subject: string;
  from: string;
  to: string;
  cc?: string;
  bcc?: string;
  date: string;
  textBody: string;
  hasHtmlAlternative: boolean;
  read: boolean;
  flagged: boolean;
  attachments: AttachmentInfo[];
}

export interface AttachmentInfo {
  name: string;
  size: number;
  type: string;
}

export interface SearchQuery {
  from?: string;
  to?: string;
  since?: string;
  before?: string;
  subject?: string;
  text?: string;
}

export interface SentEmailResult {
  messageId?: string;
  envelopeFrom?: string;
  envelopeTo: string[];
  accepted: string[];
  rejected: string[];
}

export interface ReplyContext {
  uid: number;
  folder: string;
  subject: string;
  from: string[];
  replyTo: string[];
  to: string[];
  cc: string[];
  messageId?: string;
  inReplyTo?: string;
  references: string[];
}
