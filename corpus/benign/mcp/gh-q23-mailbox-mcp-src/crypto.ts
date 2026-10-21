import { createCipheriv, createDecipheriv, createHash, randomBytes } from "crypto";

/**
 * Encrypts a JSON credential object using AES-256-GCM.
 * Returns Base64-encoded output containing IV + authTag + ciphertext.
 */
export function encrypt(plaintext: string, keyHex: string): string {
  const key = Buffer.from(keyHex, "hex");
  const iv = randomBytes(12); // 96-bit IV for GCM

  const cipher = createCipheriv("aes-256-gcm", key, iv);
  let encrypted = cipher.update(plaintext, "utf8");
  encrypted = Buffer.concat([encrypted, cipher.final()]);
  const authTag = cipher.getAuthTag();

  // Format: base64(iv + authTag + ciphertext)
  const combined = Buffer.concat([iv, authTag, encrypted]);
  return combined.toString("base64");
}

/**
 * Decrypts a Base64-encoded AES-256-GCM ciphertext.
 * Expects format: base64(iv + authTag + ciphertext)
 * Returns the decrypted plaintext.
 */
export function decrypt(encoded: string, keyHex: string): string {
  const key = Buffer.from(keyHex, "hex");
  const combined = Buffer.from(encoded, "base64");

  const iv = combined.subarray(0, 12); // 96-bit IV
  const authTag = combined.subarray(12, 28); // 128-bit auth tag
  const ciphertext = combined.subarray(28);

  const decipher = createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAuthTag(authTag);

  let decrypted = decipher.update(ciphertext);
  decrypted = Buffer.concat([decrypted, decipher.final()]);
  return decrypted.toString("utf8");
}

export function createCredentialFingerprint(user: string, pass: string): string {
  return createHash("sha256")
    .update(user)
    .update("\0")
    .update(pass)
    .digest("hex");
}

function isCredentialPayload(
  value: unknown
): value is { user: string; pass: string } {
  if (!value || typeof value !== "object") {
    return false;
  }

  const maybeCredentials = value as Record<string, unknown>;

  return (
    typeof maybeCredentials.user === "string" &&
    maybeCredentials.user.length > 0 &&
    typeof maybeCredentials.pass === "string" &&
    maybeCredentials.pass.length > 0
  );
}

/**
 * Helper to resolve encrypted credentials string into {user, pass} object.
 * Throws if decryption fails or JSON is invalid.
 */
export function resolveCredentials(
  encrypted: string,
  encryptionKey: string
): { user: string; pass: string } {
  try {
    const decrypted = decrypt(encrypted, encryptionKey);
    const parsed: unknown = JSON.parse(decrypted);

    if (!isCredentialPayload(parsed)) {
      throw new Error("Credentials missing user or pass field");
    }

    return {
      user: parsed.user,
      pass: parsed.pass,
    };
  } catch {
    throw new Error("Invalid credentials token.");
  }
}
