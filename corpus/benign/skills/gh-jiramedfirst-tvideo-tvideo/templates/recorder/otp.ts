import { existsSync, readFileSync, unlinkSync } from 'node:fs';

/**
 * Waits for the user to paste a one-time code into a file (default otp.txt, or
 * TV_OTP_FILE), returns it and deletes the file so a stale code is never reused.
 * Call it before the first tl.step (or between steps you cut): the wait is dead
 * air in the footage. The default timeout stays under the 240 s test timeout so
 * this, not Playwright, reports the missing code.
 */
export async function waitForOtp(file = process.env.TV_OTP_FILE ?? 'otp.txt', timeoutMs = 200_000): Promise<string> {
  // A file left by an earlier (failed) run holds an expired code.
  if (existsSync(file)) unlinkSync(file);
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    if (existsSync(file)) {
      // Codes are often pasted as "123 456" or "123-456".
      const code = readFileSync(file, 'utf8').replace(/[\s-]/g, '');
      if (/^[0-9A-Za-z]{4,10}$/.test(code)) {
        unlinkSync(file);
        return code;
      }
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`No one-time code (4-10 letters/digits) appeared in ${file} within ${timeoutMs / 1000}s.`);
}
