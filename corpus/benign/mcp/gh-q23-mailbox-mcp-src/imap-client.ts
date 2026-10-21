import { ImapFlow } from "imapflow";
import { simpleParser } from "mailparser";
import type { MessageAddressObject } from "imapflow";
import { createCredentialFingerprint } from "./crypto";
import { errorToMessage, logger, maskEmail } from "./logger";
import {
  ImapConfig,
  MailboxInfo,
  EmailListItem,
  EmailContent,
  SearchQuery,
  AttachmentInfo,
  ReplyContext,
} from "./types";

interface ClientPool {
  client: ImapFlow;
  user: string;
  lastActivity: number;
  inUse: boolean;
}

interface ConnectionOptions extends ImapConfig {
  user: string;
  pass: string;
}

type ConnectionFactory = (config: ConnectionOptions) => ImapFlow;

export class ImapClient {
  private globalConfig: Omit<ImapConfig, "user" | "pass">;
  private connectionPool: Map<string, ClientPool> = new Map();
  private readonly IDLE_TIMEOUT_MS = 2 * 60 * 1000; // 2 minutes
  private readonly MAX_POOL_SIZE = parseInt(process.env.MAX_POOL_SIZE || "50");
  private cleanupInterval: NodeJS.Timeout | null = null;
  private readonly connectionFactory: ConnectionFactory;

  constructor(
    config: ImapConfig,
    options?: {
      connectionFactory?: ConnectionFactory;
    }
  ) {
    this.globalConfig = {
      host: config.host,
      port: config.port,
      tls: config.tls,
    };
    this.connectionFactory =
      options?.connectionFactory ||
      ((connectionConfig): ImapFlow =>
        new ImapFlow({
          host: connectionConfig.host,
          port: connectionConfig.port,
          auth: {
            user: connectionConfig.user,
            pass: connectionConfig.pass,
          },
          secure: connectionConfig.tls,
        }));

    // Start periodic cleanup of idle connections
    this.cleanupInterval = setInterval(() => {
      void this.cleanupIdleConnections();
    }, 1 * 60 * 1000); // Check every minute
  }

  /**
   * Get or create a connection for a specific user
   */
  private async getConnection(
    poolKey: string,
    imapUser: string,
    imapPass: string
  ): Promise<ImapFlow> {
    const pool = this.connectionPool.get(poolKey);

    // If we have a usable connection, reuse it
    if (pool && pool.client.usable && !pool.inUse) {
      pool.lastActivity = Date.now();
      pool.inUse = true;
      return pool.client;
    }

    // Enforce pool size limit for new connections
    if (!pool && this.connectionPool.size >= this.MAX_POOL_SIZE) {
      throw new Error("Connection pool limit reached. Try again later.");
    }

    // Close stale connection if it exists
    if (pool && !pool.client.usable) {
      try {
        await pool.client.logout();
      } catch (error) {
        logger.warn("Failed to close stale IMAP connection", {
          user: maskEmail(imapUser),
          error: errorToMessage(error),
        });
      }
      this.connectionPool.delete(poolKey);
    }

    // Create new connection
    const client = this.connectionFactory({
      host: this.globalConfig.host,
      port: this.globalConfig.port,
      tls: this.globalConfig.tls,
      user: imapUser,
      pass: imapPass,
    });

    try {
      await client.connect();
    } catch (error) {
      logger.error("IMAP connection failed", {
        user: maskEmail(imapUser),
        error: errorToMessage(error),
      });
      throw new Error("Failed to connect to IMAP server. Check credentials and server settings.");
    }

    // Store in pool
    this.connectionPool.set(poolKey, {
      client,
      user: imapUser,
      lastActivity: Date.now(),
      inUse: true,
    });

    return client;
  }

  /**
   * Release a connection back to the pool
   */
  private releaseConnection(poolKey: string): void {
    const pool = this.connectionPool.get(poolKey);
    if (pool) {
      pool.inUse = false;
      pool.lastActivity = Date.now();
    }
  }

  /**
   * Clean up idle connections
   */
  private async cleanupIdleConnections(): Promise<void> {
    const now = Date.now();
    const keysToDelete: string[] = [];

    for (const [key, pool] of this.connectionPool.entries()) {
      if (!pool.inUse && now - pool.lastActivity > this.IDLE_TIMEOUT_MS) {
        try {
          await pool.client.logout();
        } catch (error) {
          logger.warn("Failed to close idle IMAP connection", {
            user: maskEmail(pool.user),
            error: errorToMessage(error),
          });
        }
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach((key) => this.connectionPool.delete(key));
  }

  /**
   * Execute a function with an IMAP connection, automatically releasing it
   */
  private async withConnection<T>(
    imapUser: string,
    imapPass: string,
    fn: (client: ImapFlow) => Promise<T>
  ): Promise<T> {
    const poolKey = createCredentialFingerprint(imapUser, imapPass);
    const client = await this.getConnection(poolKey, imapUser, imapPass);
    try {
      return await fn(client);
    } finally {
      this.releaseConnection(poolKey);
    }
  }

  async disconnect(): Promise<void> {
    // Clear cleanup interval
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }

    // Close all connections
    for (const [, pool] of this.connectionPool.entries()) {
      try {
        await pool.client.logout();
      } catch (error) {
        logger.warn("Failed to close IMAP connection during shutdown", {
          user: maskEmail(pool.user),
          error: errorToMessage(error),
        });
      }
    }
    this.connectionPool.clear();
  }

  async listFolders(imapUser: string, imapPass: string): Promise<MailboxInfo[]> {
    return this.withConnection(imapUser, imapPass, async (client) => {
      const mailboxes = await client.list();
      const folders: MailboxInfo[] = [];

      for (const mailbox of mailboxes) {
        const folder: MailboxInfo = {
          name: mailbox.name || "Unknown",
          path: mailbox.path || "",
          messageCount: mailbox.status?.messages || 0,
          unreadCount: mailbox.status?.unseen || 0,
        };
        folders.push(folder);
      }

      return folders;
    });
  }

  async listEmails(
    imapUser: string,
    imapPass: string,
    folder: string,
    limit: number,
    offset: number,
    filter?: { since?: string; before?: string }
  ): Promise<EmailListItem[]> {
    return this.withConnection(imapUser, imapPass, async (client) => {
      try {
        await client.mailboxOpen(folder);
      } catch (error) {
        throw new Error(
          `Failed to open folder "${folder}": ${errorToMessage(error)}`
        );
      }

      // Get message UIDs in reverse order (newest first)
      const searchFilter: Record<string, unknown> = {};
      if (filter?.since) {
        searchFilter.since = new Date(filter.since);
      }
      if (filter?.before) {
        searchFilter.before = new Date(filter.before);
      }

      const uids = await client.search(
        Object.keys(searchFilter).length > 0 ? searchFilter : { all: true },
        { uid: true }
      );
      const reversedUids = Array.isArray(uids) ? uids : [];
      const selectedUids = reversedUids
        .slice(
          Math.max(0, reversedUids.length - limit - offset),
          reversedUids.length - offset || undefined
        )
        .reverse();

      const emails: EmailListItem[] = [];

      for (const uid of selectedUids) {
        try {
          const message = await client.fetchOne(
            uid,
            { source: false, envelope: true, flags: true },
            { uid: true }
          );

          if (message && message.envelope) {
            const envelope = message.envelope;
            const flags = message.flags || new Set<string>();
            emails.push({
              uid: message.uid,
              subject: envelope.subject || "(no subject)",
              from: envelope.from?.[0]?.address || "unknown",
              to: envelope.to?.[0]?.address || "unknown",
              date: envelope.date ? new Date(envelope.date).toISOString() : "",
              read: flags.has("\\Seen"),
              flagged: flags.has("\\Flagged"),
              messageId: envelope.messageId || undefined,
            });
          }
        } catch (error) {
          logger.warn("Skipping email after IMAP fetch error", {
            user: maskEmail(imapUser),
            uid,
            error: errorToMessage(error),
          });
          continue;
        }
      }

      return emails;
    });
  }

  async searchEmails(
    imapUser: string,
    imapPass: string,
    folder: string,
    query: string | undefined,
    searchQuery: SearchQuery,
    limit: number,
    sortOrder: "asc" | "desc" = "desc"
  ): Promise<EmailListItem[]> {
    return this.withConnection(imapUser, imapPass, async (client) => {
      try {
        await client.mailboxOpen(folder);
      } catch (error) {
        throw new Error(
          `Failed to open folder "${folder}": ${errorToMessage(error)}`
        );
      }

      // Build IMAP search query
      const searchCriteria: Record<string, unknown> = {};

      if (query) {
        searchCriteria.text = query;
      }

      if (searchQuery.from) {
        searchCriteria.from = searchQuery.from;
      }

      if (searchQuery.to) {
        searchCriteria.to = searchQuery.to;
      }

      if (searchQuery.subject) {
        searchCriteria.subject = searchQuery.subject;
      }

      if (searchQuery.since) {
        searchCriteria.since = new Date(searchQuery.since);
      }

      if (searchQuery.before) {
        searchCriteria.before = new Date(searchQuery.before);
      }

      // Perform search (uid: true returns UIDs instead of sequence numbers)
      const uids = await client.search(searchCriteria, { uid: true });
      const reversedUids = Array.isArray(uids) ? uids : [];
      const selectedUids = sortOrder === "desc"
        ? reversedUids.slice(-limit).reverse()  // newest N, displayed newest-first
        : reversedUids.slice(0, limit);          // oldest N, displayed oldest-first

      const emails: EmailListItem[] = [];

      for (const uid of selectedUids) {
        try {
          const message = await client.fetchOne(
            uid,
            { source: false, envelope: true, flags: true },
            { uid: true }
          );

          if (message && message.envelope) {
            const envelope = message.envelope;
            const flags = message.flags || new Set<string>();
            emails.push({
              uid: message.uid,
              subject: envelope.subject || "(no subject)",
              from: envelope.from?.[0]?.address || "unknown",
              to: envelope.to?.[0]?.address || "unknown",
              date: envelope.date ? new Date(envelope.date).toISOString() : "",
              read: flags.has("\\Seen"),
              flagged: flags.has("\\Flagged"),
              messageId: envelope.messageId || undefined,
            });
          }
        } catch (error) {
          logger.warn("Skipping search result after IMAP fetch error", {
            user: maskEmail(imapUser),
            uid,
            error: errorToMessage(error),
          });
          continue;
        }
      }

      return emails;
    });
  }

  async readEmail(
    imapUser: string,
    imapPass: string,
    folder: string,
    uid: number
  ): Promise<EmailContent> {
    return this.withConnection(imapUser, imapPass, async (client) => {
      try {
        await client.mailboxOpen(folder);
      } catch (error) {
        throw new Error(
          `Failed to open folder "${folder}": ${errorToMessage(error)}`
        );
      }

      let message;
      try {
        message = await client.fetchOne(
          uid,
          { source: true, envelope: true, flags: true },
          { uid: true }
        );
      } catch (error) {
        throw new Error(
          `Failed to fetch message ${uid}: ${errorToMessage(error)}`
        );
      }

      if (!message) {
        throw new Error(`Message ${uid} not found in folder "${folder}"`);
      }

      const envelope = message.envelope;
      const flags = message.flags || new Set<string>();
      const attachments: AttachmentInfo[] = [];

      const rawSource = message.source;
      const parsed = rawSource ? await simpleParser(rawSource) : null;

      const textBody = parsed?.text?.substring(0, 5000) || "";
      const hasHtmlAlternative = Boolean(parsed?.html);

      return {
        uid: message.uid,
        subject: envelope?.subject || parsed?.subject || "(no subject)",
        from: envelope?.from?.[0]?.address || parsed?.from?.value?.[0]?.address || "unknown",
        to: envelope?.to?.[0]?.address || (Array.isArray(parsed?.to) ? parsed?.to?.[0]?.value?.[0]?.address : parsed?.to?.value?.[0]?.address) || "unknown",
        cc: envelope?.cc?.[0]?.address,
        bcc: envelope?.bcc?.[0]?.address,
        date: envelope?.date ? new Date(envelope.date).toISOString() : "",
        textBody,
        hasHtmlAlternative,
        read: flags.has("\\Seen"),
        flagged: flags.has("\\Flagged"),
        attachments,
      };
    });
  }

  async getReplyContext(
    imapUser: string,
    imapPass: string,
    folder: string,
    uid: number
  ): Promise<ReplyContext> {
    return this.withConnection(imapUser, imapPass, async (client) => {
      try {
        await client.mailboxOpen(folder);
      } catch (error) {
        throw new Error(
          `Failed to open folder "${folder}": ${errorToMessage(error)}`
        );
      }

      const message = await client.fetchOne(
        uid,
        { source: true, envelope: true },
        { uid: true }
      );

      if (!message) {
        throw new Error(`Message ${uid} not found in folder "${folder}"`);
      }

      const src = message.source;
      const sourceText = src
        ? Buffer.isBuffer(src)
          ? src.toString("utf8")
          : typeof src === "string"
          ? src
          : Buffer.from((src as Uint8Array).buffer, (src as Uint8Array).byteOffset, (src as Uint8Array).byteLength).toString("utf8")
        : "";
      const headers = this.extractHeaders(sourceText);
      const envelope = message.envelope;

      const replyTo = this.mapAddresses(envelope?.replyTo);
      const fallbackReplyTo =
        replyTo.length > 0
          ? replyTo
          : this.extractEmailAddresses(headers.get("reply-to"));

      const referencesHeader = headers.get("references");
      const references = referencesHeader
        ? referencesHeader.split(/\s+/).filter(Boolean)
        : [];

      return {
        uid: message.uid,
        folder,
        subject: envelope?.subject || "(no subject)",
        from: this.mapAddresses(envelope?.from),
        replyTo: fallbackReplyTo,
        to: this.mapAddresses(envelope?.to),
        cc: this.mapAddresses(envelope?.cc),
        messageId: envelope?.messageId || headers.get("message-id"),
        inReplyTo: envelope?.inReplyTo || headers.get("in-reply-to"),
        references,
      };
    });
  }

  private extractHeaders(source: string): Map<string, string> {
    const headers = new Map<string, string>();
    const lines = source.split(/\r?\n/);
    let currentName: string | null = null;
    let currentValue = "";

    for (const line of lines) {
      if (line.trim() === "") {
        break;
      }

      if (/^\s/.test(line) && currentName) {
        currentValue += ` ${line.trim()}`;
        continue;
      }

      if (currentName) {
        headers.set(currentName, currentValue.trim());
      }

      const separator = line.indexOf(":");
      if (separator === -1) {
        currentName = null;
        currentValue = "";
        continue;
      }

      currentName = line.slice(0, separator).trim().toLowerCase();
      currentValue = line.slice(separator + 1).trim();
    }

    if (currentName) {
      headers.set(currentName, currentValue.trim());
    }

    return headers;
  }

  private mapAddresses(addresses?: MessageAddressObject[]): string[] {
    return (addresses || [])
      .map((address) => address.address)
      .filter((address): address is string => Boolean(address));
  }

  private extractEmailAddresses(headerValue?: string): string[] {
    if (!headerValue) {
      return [];
    }

    return headerValue.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];
  }
}
