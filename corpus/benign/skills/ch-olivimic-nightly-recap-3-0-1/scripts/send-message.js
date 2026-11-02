#!/usr/bin/env node
/**
 * send-message.js
 * Nightly Recap, Telegram delivery script
 *
 * Sends a single message to a Telegram chat.
 * Reads credentials from config.json OR from CLI flags.
 *
 * Usage (from config.json):
 *   node send-message.js --message "Your message here"
 *
 * Usage (explicit credentials):
 *   node send-message.js --token "BOT_TOKEN" --chat "CHAT_ID" --message "Your message here"
 *
 * Usage (from stdin, pipe a message in):
 *   echo "Your message" | node send-message.js
 */

if (parseInt(process.version.slice(1)) < 18) {
  console.error('[nightly-recap] Error: Node.js 18+ required. Current: ' + process.version + '. Download at https://nodejs.org');
  process.exit(1);
}

const fs = require('fs');
const path = require('path');
const https = require('https');

// ─── Parse CLI args ───────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const getArg = (flag) => {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : null;
};

let [REDACTED_SECRET]'--token');
let chatId = getArg('--chat');
let message = getArg('--message');

// ─── Load from config.json if credentials not provided via CLI ────────────────

if (!token || !chatId) {
  const configPath = path.join(__dirname, '..', 'config.json');
  if (!fs.existsSync(configPath)) {
    console.error('[nightly-recap] ERROR: config.json not found.');
    console.error('  Run setup: say "reconfigure nightly-recap" in OpenClaw.');
    console.error('  Or provide --token and --chat flags explicitly.');
    process.exit(1);
  }

  let config;
  try {
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  } catch (err) {
    console.error('[nightly-recap] ERROR: Failed to parse config.json:', err.message);
    process.exit(1);
  }

  if (!token) [REDACTED_SECRET];
  if (!chatId) chatId = config.telegramChatId;
}

// ─── Validate credentials ─────────────────────────────────────────────────────

const PLACEHOLDER_PATTERN = /^YOUR_/i;

if (!token || PLACEHOLDER_PATTERN.test(token)) {
  console.error('[nightly-recap] ERROR: telegramBotToken is not configured.');
  console.error('  Say "reconfigure nightly-recap" to set it up.');
  process.exit(1);
}

if (!chatId || PLACEHOLDER_PATTERN.test(chatId)) {
  console.error('[nightly-recap] ERROR: telegramChatId is not configured.');
  console.error('  Say "reconfigure nightly-recap" to set it up.');
  process.exit(1);
}

// ─── Read message from stdin if not provided ──────────────────────────────────

async function readStdin() {
  return new Promise((resolve) => {
    if (process.stdin.isTTY) return resolve(null);
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data.trim() || null));
  });
}

// ─── Send to Telegram ─────────────────────────────────────────────────────────

function sendTelegram(botToken, chat, text) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({
      chat_id: chat,
      text: text,
      parse_mode: 'HTML',
    });

    const options = {
      hostname: 'api.telegram.org',
      port: 443,
      path: `/bot${botToken}/sendMessage`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(body);
          if (parsed.ok) {
            resolve(parsed);
          } else {
            reject(new Error(`Telegram API error ${res.statusCode}: ${parsed.description || body}`));
          }
        } catch (e) {
          reject(new Error(`Failed to parse Telegram response: ${body}`));
        }
      });
    });

    req.on('error', (err) => reject(err));
    req.write(payload);
    req.end();
  });
}

// ─── Main ─────────────────────────────────────────────────────────────────────

(async () => {
  // Fall back to stdin if no --message flag
  if (!message) {
    message = await readStdin();
  }

  if (!message || !message.trim()) {
    console.error('[nightly-recap] ERROR: No message provided.');
    console.error('  Use --message "text" or pipe a message via stdin.');
    process.exit(1);
  }

  try {
    const result = await sendTelegram(token, chatId, message.trim());
    console.log(`[nightly-recap] ✓ Message delivered (message_id: ${result.result.message_id})`);
  } catch (err) {
    console.error('[nightly-recap] DELIVERY FAILED:', err.message);

    if (err.message.includes('401')) {
      console.error('  → telegramBotToken is invalid or revoked. Get a new one from @BotFather.');
    } else if (err.message.includes('400')) {
      console.error('  → telegramChatId may be wrong. Verify with @userinfobot on Telegram.');
    } else if (err.message.includes('chat not found')) {
      console.error('  → Chat not found. Make sure you\'ve sent /start to your bot first.');
    }

    console.error('  → Run "reconfigure nightly-recap" to update credentials.');
    process.exit(1);
  }
})();
