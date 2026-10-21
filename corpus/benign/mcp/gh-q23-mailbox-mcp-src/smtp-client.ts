import nodemailer from "nodemailer";
import type { SendMailOptions } from "nodemailer";
import type { SentEmailResult, SmtpConfig } from "./types";

function stringifyAddress(
  address: string | { address?: string; name?: string }
): string {
  if (typeof address === "string") {
    return address;
  }

  return address.address || address.name || "";
}

export class SmtpClient {
  constructor(private readonly config: SmtpConfig) {}

  async sendEmail(
    smtpUser: string,
    smtpPass: string,
    message: SendMailOptions
  ): Promise<SentEmailResult> {
    const secure = this.config.port === 465;
    const transporter = nodemailer.createTransport({
      host: this.config.host,
      port: this.config.port,
      secure,
      requireTLS: secure ? undefined : this.config.tls,
      auth: {
        user: smtpUser,
        pass: smtpPass,
      },
    });

    const info = await transporter.sendMail(message);

    return {
      messageId: info.messageId,
      envelopeFrom:
        typeof info.envelope?.from === "string" ? info.envelope.from : undefined,
      envelopeTo: info.envelope?.to || [],
      accepted: (info.accepted || [])
        .map((address) => stringifyAddress(address))
        .filter(Boolean),
      rejected: (info.rejected || [])
        .map((address) => stringifyAddress(address))
        .filter(Boolean),
    };
  }
}
