# JsonLogic Skill

An **agent skill** that teaches AI coding assistants to work with [JsonLogic](https://jsonlogic.com) business rules: turn a plain-language requirement into a valid JsonLogic rule, run it, validate it, explain it, or debug it.

Works with **Claude Code, Cursor, GitHub Copilot, VS Code, Codex, and Gemini CLI**. Install it once and your AI assistant picks it up automatically whenever JsonLogic comes up, in any project.

[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-jsonlogic-6366F1)](https://agentskills.io)

![Demo of the jsonlogic skill turning a business rule into a validated JsonLogic expression](assets/demo.gif)

## Install

**Claude Code:**

```bash
git clone https://github.com/valeryia-piatrova/jsonlogic-skill.git ~/.claude/skills/jsonlogic
```

Restart Claude Code to pick it up.

**Every install path differs by client:** each badge below jumps to that client's
exact command in [docs/installing.md](docs/installing.md):

[![Cursor](https://img.shields.io/badge/Cursor-Install-lightgrey)](docs/installing.md#cursor)
[![GitHub Copilot](https://img.shields.io/badge/Copilot-Install-lightgrey)](docs/installing.md#github-copilot)
[![VS Code](https://img.shields.io/badge/VS%20Code-Install-lightgrey)](docs/installing.md#vs-code)
[![Codex](https://img.shields.io/badge/Codex-Install-lightgrey)](docs/installing.md#codex)
[![Gemini CLI](https://img.shields.io/badge/Gemini%20CLI-Install-lightgrey)](docs/installing.md#gemini-cli)

## What It Does

Your AI assistant uses this JsonLogic skill automatically when JsonLogic comes up.

- Turn a plain-language business requirement into a valid JsonLogic rule
- Run a JsonLogic rule against your data
- Validate whether a JsonLogic rule is well-formed
- Explain what an existing JsonLogic rule does
- Debug a JsonLogic rule that returns the wrong result

## Usage

**No data shape given:**

> Give a 20% discount on orders over $200, or 10% over $100, otherwise no discount

> Approve a claim only if the policy is active and the incident happened after the policy start date, but route it to manual review instead if the policyholder already has 2+ claims this year, or if the amount is over the coverage limit

> Let a user edit a document if they are the owner or an admin, but only while the document is not locked for review

> Flag a transaction as suspicious if it is over $5,000 and happens outside business hours, unless the account has 90+ days of history and no prior flags, in which case just log it instead of blocking

**Data shape given (field names come from it, not a guess):**

> Approve a claim, but route it to manual review instead of auto-approving if the policyholder already has 2+ claims this year or the amount is over the limit.

> Explain what this JsonLogic rule does:

```json
{
	"some": [
		{ "var": "items" },
		{ ">": [{ "var": "price" }, 500] }
	]
}
```

> Run this JsonLogic rule in Ruby:

```json
{
	">=": [{ "var": "age" }, 18]
}
```

> Why does this rule return `false` when I expect `true`?

```json
{
	"rule": { "and": [
		{ ">": [{ "var": "total" }, 100] },
		{ "==": [{ "var": "vip" }, true] }
	]},
	"data": { "total": 150, "vip": "true" }
}
```

Uses operators from the real JsonLogic standard. Checks whether the standard and
your language's library actually support the logic you need, and says so plainly if they don't.

## FAQ

**What is the JsonLogic skill?**

An open-source agent skill (MIT licensed) that gives AI coding assistants reliable JsonLogic abilities: writing, running, validating, explaining, and debugging JsonLogic business rules.

**Which AI assistants does it work with?**

Claude Code, Cursor, GitHub Copilot, VS Code (agent mode), Codex, and Gemini CLI, plus any other client that supports the open Agent Skills format from agentskills.io.

**What is JsonLogic?**

[JsonLogic](https://jsonlogic.com) is a JSON-based format for portable business rules and conditional logic. One rule runs across JavaScript, Python, Ruby, PHP, Java, and more.

**How is this different from asking ChatGPT or Claude to write JsonLogic directly?**

The skill encodes the real JsonLogic standard, per-language operator support, and a validate-before-you-answer workflow, so you get rules that actually run instead of plausible-looking guesses.

**Do I need to install anything else?**

No. The skill is a folder of Markdown plus small scripts. Clone it into your client's skills directory and restart the client.

**Is it free?**

Yes. MIT license, free for personal and commercial use.

## Learn More

- [jsonlogic.com](https://jsonlogic.com): the standard this skill implements
- [`SKILL.md`](SKILL.md): full workflow and reasoning

## License

MIT, see [`LICENSE`](LICENSE).
