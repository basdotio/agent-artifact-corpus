---
name: rumoro-triage
description: Go through new Rumoro mentions inside Claude Code. Fetches the relevant posts from the last day, sorts them into buying signals, questions and problems, drafts replies or GitHub issues for the mentions the user chooses, and records what was handled. Use when the user asks what's new, what people say about the product, or wants to clear their mentions.
---

# Rumoro triage

The tools named here come from the Rumoro MCP server. This skill never posts anything, because the user publishes replies themselves.

If the Rumoro tools are missing or return `Unauthorized`, the sign-in failed, so don't tell the user they're connected. Ask them to run `claude mcp add --transport http rumoro https://mcp.rumoro.dev/mcp`, then open `/mcp`, choose `rumoro` and Authenticate, or to use the API-key option in this repository's README.

## 1. Collect

Call `search_mentions` with `status: "open"`, `relevant: true`, `sort: "priority"` and `limit: 50`, and set `since` to the start of yesterday in the user's timezone (ISO 8601). If the user asked about one platform or keyword, add `platforms` or `keywordIds`.

Also call `list_keywords` with `kind: ["competitor"]` and no `limit`, so every competitor keyword comes back. Keep their `id`s. A mention whose `keyword.id` is one of them is about a competitor.

## 2. Sort

Every mention goes in exactly one group. Check the groups in this order.

1. **Buying signals** have `buy_intent` in `classification.intents`, or `churn_intent` on a competitor keyword (someone leaving a competitor).
2. **Questions** have the intent `question`.
3. **Problems** have `bug_report` or `complaint`, or are reviews with a `review.rating` of 1 or 2.
4. **Other** holds everything else.

Show each mention on one line with `post.platform`, the author (`author.name` or `author.handle`, and `author.followers` when known), a one-sentence summary and `post.url`. Add `classification.note` in brackets when it explains the score.

If the search is empty, tell the user and suggest `get_mention_stats` over the past week instead.

## 3. Act on the user's picks

- To reply, write a draft that helps the person first and fits the platform's tone. If the draft mentions the product, it says the user works on it. If the project's `CLAUDE.md` sets reply rules or a voice, follow them. Show the draft and don't post it.
- For a bug in this codebase, find where it probably lives and draft a GitHub issue with a title, steps to reproduce and the link to the post.
- For a post that isn't relevant, set `relevant: false` with `update_mention`, which records the correction.
- To come back to a post later, call `update_mention` with `snoozedUntil`. The mention stays out of the feed until the time the user picks.

## 4. Wrap up

Once the user confirms a mention is handled, call `update_mention` with `status: "done"`. For noise, use `status: "ignored"`. End with how many mentions were handled, ignored and left open.
