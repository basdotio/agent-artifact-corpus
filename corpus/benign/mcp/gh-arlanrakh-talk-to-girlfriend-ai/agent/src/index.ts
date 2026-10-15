#!/usr/bin/env bun
/**
 * Telegram AI Agent CLI
 * Interactive chatbox for communicating via Telegram with AI assistance
 */

import * as p from "@clack/prompts";
import pc from "picocolors";
import { chat, clearHistory, getHistoryLength } from "./agent";
import { config, validateConfig } from "./config";

// ASCII art banner
const BANNER = `
${pc.cyan("╔════════════════════════════════════════════╗")}
${pc.cyan("║")}  ${pc.bold(pc.magenta("🤖 Telegram AI Agent"))}                     ${pc.cyan("║")}
${pc.cyan("║")}  ${pc.dim("Your AI wingman for Telegram")}               ${pc.cyan("║")}
${pc.cyan("╚════════════════════════════════════════════╝")}
`;

// Help text
const HELP_TEXT = `
${pc.bold("Commands:")}
  ${pc.yellow("/help")}     - Show this help message
  ${pc.yellow("/clear")}    - Clear conversation history
  ${pc.yellow("/status")}   - Check connection status
  ${pc.yellow("/quit")}     - Exit the agent

${pc.bold("Example prompts:")}
  ${pc.dim("• Show me my recent chats")}
  ${pc.dim("• Read the last 5 messages from @username")}
  ${pc.dim("• What should I reply to her message about coffee?")}
  ${pc.dim("• Send 'Good morning beautiful ☀️' to @username")}
  ${pc.dim("• AI-ify her message 'I miss you' in a flirty way")}
`;

async function checkTelegramConnection(): Promise<boolean> {
  try {
    const response = await fetch(`${config.telegramApiUrl}/health`);
    if (response.ok) {
      const data = await response.json();
      return data.connected === true;
    }
    return false;
  } catch {
    return false;
  }
}

async function main() {
  console.clear();
  console.log(BANNER);

  // Validate configuration
  validateConfig();

  p.intro(pc.bgCyan(pc.black(" Welcome to your Telegram AI Agent ")));

  // Check Telegram connection
  const connectionSpinner = p.spinner();
  connectionSpinner.start("Checking Telegram connection...");

  const isConnected = await checkTelegramConnection();

  if (isConnected) {
    connectionSpinner.stop(pc.green("✓ Telegram connected"));
  } else {
    connectionSpinner.stop(pc.yellow("⚠ Telegram API not connected"));
    p.note(
      `Start the Telegram API bridge first:\n${pc.cyan("python telegram_api.py")}`,
      "Setup Required"
    );
  }

  // Show config status
  const configStatus = [
    `Model: ${pc.cyan(config.model)}`,
    `Telegram API: ${pc.cyan(config.telegramApiUrl)}`,
    `Nia Source: ${config.niaCodebaseSource ? pc.green("✓ Configured") : pc.yellow("Not set")}`,
  ].join("\n");

  p.note(configStatus, "Configuration");

  console.log(HELP_TEXT);

  // Main chat loop
  while (true) {
    const input = await p.text({
      message: pc.cyan("You"),
      placeholder: "Type your message or /help for commands...",
    });

    // Handle cancellation (Ctrl+C)
    if (p.isCancel(input)) {
      p.outro(pc.dim("Goodbye! 👋"));
      process.exit(0);
    }

    const message = (input as string).trim();

    if (!message) continue;

    // Handle commands
    if (message.startsWith("/")) {
      const command = message.toLowerCase();

      switch (command) {
        case "/help":
          console.log(HELP_TEXT);
          continue;

        case "/clear":
          clearHistory();
          p.log.success("Conversation history cleared");
          continue;

        case "/status":
          const connected = await checkTelegramConnection();
          p.log.info(
            connected
              ? pc.green("Telegram: Connected ✓")
              : pc.red("Telegram: Not connected ✗")
          );
          p.log.info(`Messages in history: ${getHistoryLength()}`);
          continue;

        case "/quit":
        case "/exit":
        case "/q":
          p.outro(pc.dim("Goodbye! 👋"));
          process.exit(0);

        default:
          p.log.warn(`Unknown command: ${command}. Type /help for available commands.`);
          continue;
      }
    }

    // Process with AI agent
    const spinner = p.spinner();
    spinner.start(pc.dim("Thinking..."));

    try {
      const stream = await chat(message);
      spinner.stop(pc.magenta("Agent"));

      // Stream the response
      let response = "";
      process.stdout.write(pc.dim("  "));

      for await (const chunk of stream) {
        process.stdout.write(chunk);
        response += chunk;
      }

      console.log("\n");
    } catch (error: any) {
      spinner.stop(pc.red("Error"));

      if (error.message?.includes("Telegram API")) {
        p.log.error(
          `Telegram API error. Make sure the bridge is running:\n${pc.cyan("python telegram_api.py")}`
        );
      } else if (error.message?.includes("AI_GATEWAY")) {
        p.log.error("AI Gateway error. Check your AI_GATEWAY_API_KEY.");
      } else {
        p.log.error(error.message || "An unexpected error occurred");
      }
    }
  }
}

// Run
main().catch((error) => {
  console.error(pc.red("Fatal error:"), error);
  process.exit(1);
});
