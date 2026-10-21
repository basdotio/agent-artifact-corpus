/**
 * Read-only MCP server for vas3k.club. Mounted at `/mcp`.
 *
 * Surface
 * -------
 * - 12 tools wrapping the `*.json` / `*.md` endpoints under reference/.
 * - 2 resources for "always-on" context: `vas3k://me` (the authenticated
 *   member's profile, fetched lazily when the client subscribes) and
 *   `vas3k://about` (server capability summary, the same content an
 *   integrating agent gets from `/install.md`).
 * - 1 prompt template `weekly_digest` for guided "summarize the club this
 *   week" runs.
 *
 * Implementation notes
 * --------------------
 * Tools delegate to {@link Vas3kClient}, constructed lazily per call using
 * `this.props.upstreamAccessToken` (set by `OAuthProvider`). Each tool with
 * a stable response shape registers an `outputSchema` from `src/schemas.ts`,
 * so MCP clients receive both the structured object (for typed access by the
 * model) and a text JSON fallback (for older clients). Tool descriptions are
 * written for the LLM, not the human — they explain when to call the tool,
 * what the response looks like, and which fields chain into other tools.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { McpAgent } from "agents/mcp";
import { z } from "zod";

import { MCP_SERVER_NAME, MCP_SERVER_VERSION } from "./constants";
import {
  commentsResponseShape,
  feedShape,
  ORDERING_VALUES,
  POST_TYPE_VALUES,
  postResponseShape,
  searchTagsResponseShape,
  searchUsersResponseShape,
  TAG_GROUP_VALUES,
  userAchievementsResponseShape,
  userBadgesResponseShape,
  userResponseShape,
  userTagsResponseShape,
} from "./schemas";
import type { Env, Props } from "./types";
import { Vas3kAPIError, Vas3kClient } from "./vas3k-client";

const POST_TYPE = z
  .enum(POST_TYPE_VALUES)
  .describe(
    "Post type. Must match the post's actual type (the slug alone is not enough — calling /question/<slug> on a post of type 'project' returns 302).",
  );

const FEED_POST_TYPE = z
  .enum(["all", ...POST_TYPE_VALUES])
  .default("all")
  .describe("Filter the feed to a single post type, or 'all' for the global feed.");

const ORDERING = z
  .enum(ORDERING_VALUES)
  .describe(
    "Feed ordering. 'activity' = recent comments first; 'new' = recent posts; 'top*' = highest upvoted in window; 'hot' = trending.",
  );

const TAG_GROUP = z
  .enum(TAG_GROUP_VALUES)
  .describe("Profile-tag category — see search_tags output for the full taxonomy.");

const SLUG = z
  .string()
  .describe(
    "URL slug — letters, digits, '_' or '-'. For users, this is the handle in their profile URL (e.g. 'vas3k' for vas3k.club/user/vas3k/).",
  );

/**
 * Read tools hit upstream HTTP and never mutate. The `idempotentHint` and
 * `destructiveHint` fields are deliberately omitted — the spec says they're
 * meaningful only when `readOnlyHint == false`, and adding them on a read
 * tool just clutters the wire.
 */
const READ_ANNOTATIONS = { readOnlyHint: true, openWorldHint: true } as const;

/**
 * Strip any bearer-token-shaped or session-token-shaped substring from text
 * before sending it to the LLM. Defence against the rare case where vas3k.club
 * echoes the Authorization header in an error body (security review P2-2).
 */
function redactSecrets(s: string): string {
  return s
    .replace(/Bearer\s+\S+/gi, "Bearer [REDACTED]")
    .replace(/\b(st|sa)_[A-Za-z0-9_-]+/g, "$1_[REDACTED]")
    .replace(/"(access_token|refresh_token|id_token)"\s*:\s*"[^"]+"/g, '"$1":"[REDACTED]"');
}

/**
 * Threshold-only operational logging for tool calls.
 *
 * Wraps `server.registerTool` once: every subsequent registration's handler
 * is invisibly tagged with a "did the response come back oversized or slow?"
 * check. No log lines fire on the happy path; if a tool result crosses
 * either threshold (size > {@link LARGE_RESULT_BYTES} or duration >
 * {@link SLOW_TOOL_MS}) we emit a single `[tool large/slow]` warning with
 * `name`, `ms`, `size`, `isError`. **Crucially, no user data, arguments, or
 * response content** — just envelope shape. This is the canary that warned
 * us about the 4 MB get_feed response (1.1.0 regression caught 2026-04-20).
 *
 * Why patch `registerTool` instead of touching wrap/wrapStructured: this
 * captures the tool name automatically, in one place, without editing 23
 * call sites.
 */
const LARGE_RESULT_BYTES = 250_000;
const SLOW_TOOL_MS = 3_000;

function instrumentRegisterTool(server: McpServer): void {
  const orig = server.registerTool.bind(server);
  // The SDK's registerTool generics are a tangle of overloads — `as any` keeps
  // the wrapper one-line and the public type signature unchanged downstream.
  server.registerTool = ((name: string, config: any, handler: any) => {
    return orig(name, config, async (...args: unknown[]) => {
      const start = Date.now();
      const result: any = await handler(...args);
      const ms = Date.now() - start;
      const size = JSON.stringify(result).length;
      if (size > LARGE_RESULT_BYTES || ms > SLOW_TOOL_MS) {
        console.warn("[tool large/slow]", { name, ms, size, isError: !!result.isError });
      }
      return result;
    });
  }) as any;
}

/**
 * Format an exception into a CallToolResult error payload. Module-level
 * (not a method) so {@link MyMCP.wrap} stays self-contained and the unit
 * test in `test/mcp-wrap.test.ts` can exercise it with an empty `this`.
 */
function toolError(err: unknown) {
  if (err instanceof Vas3kAPIError) {
    const hint =
      err.status === 401
        ? " (token expired — try again after refresh)"
        : err.status === 403
          ? " (your account does not have access)"
          : err.status === 404
            ? " (not found — check the slug)"
            : err.status === 429
              ? " (rate limited)"
              : err.status >= 500
                ? " (upstream is having problems — retry later)"
                : "";
    const payload = redactSecrets(JSON.stringify(err.payload).slice(0, 500));
    return {
      isError: true,
      content: [
        {
          type: "text" as const,
          text: `vas3k.club returned ${err.status}${hint}: ${payload}`,
        },
      ],
    };
  }
  const e = err as Error;
  console.error("[mcp tool failure]", e.name, e.message, e.stack);
  return {
    isError: true,
    content: [
      {
        type: "text" as const,
        text: `Unexpected error (${e.name}): ${redactSecrets(e.message)}`,
      },
    ],
  };
}

/**
 * Static markdown served via the `vas3k://about` resource. Mirrors the
 * landing-page tool grouping so an agent reading this resource learns the
 * same surface a human would see at https://vas3k-mcp.rmbk.me/.
 */
const ABOUT_MARKDOWN = `# vas3k-mcp

Remote MCP server for [vas3k.club](https://vas3k.club). Two endpoints share one OAuth registration:

- \`/mcp\` — read-only. Profiles, posts, feeds, comments, search.
- \`/mcp-full\` — read + write (votes, bookmarks, friend requests, room subscriptions, profile-tag toggles).

Authentication is OAuth 2.1 against vas3k.club. Tokens are issued and refreshed transparently by the worker.

## Tool naming conventions

- \`get_*\` — single resource by id/slug
- \`list_*\` / \`search_*\` — collections
- \`*_post\` / \`*_comment\` / \`*_room\` — write actions on the named entity (only on \`/mcp-full\`)

## Common workflows

- "Who is X?" → \`search_users\` → \`get_user\` (+ \`get_user_tags\`, \`get_user_badges\`)
- "What's new in topic X?" → \`search_tags\` → \`get_feed\` (filtered)
- "Summarize this thread" → \`get_post_markdown\` + \`list_post_comments\`
- "Find people doing X" → \`search_tags\` (group=tech/hobbies) for the tag, then humans by tag membership

The full reference for every tool — name, args, output schema — is exposed via \`tools/list\`.`;

export class MyMCP extends McpAgent<Env, Record<string, never>, Props> {
  server = new McpServer({ name: MCP_SERVER_NAME, version: MCP_SERVER_VERSION });

  protected client(): Vas3kClient {
    // OAuthProvider should populate `props` for any request that reaches an
    // apiHandler-mounted tool. Guard anyway so a revoked token surfaces as a
    // structured error rather than a runtime TypeError (code review P2-4).
    if (!this.props) {
      throw new Vas3kAPIError(401, {
        error: "no props — token revoked or upstream session expired",
      });
    }
    return new Vas3kClient({
      baseUrl: this.env.VAS3K_BASE_URL,
      accessToken: this.props.upstreamAccessToken,
    });
  }

  /** Wrap a tool whose result is text or arbitrary JSON (no `outputSchema`). */
  protected async wrap<T>(fn: () => Promise<T>) {
    try {
      const data = await fn();
      const text = typeof data === "string" ? data : JSON.stringify(data);
      return { content: [{ type: "text" as const, text }] };
    } catch (err) {
      return toolError(err);
    }
  }

  /**
   * Wrap a tool that has a registered `outputSchema`. Returns BOTH
   * `structuredContent` (modern clients consume this directly, with type
   * info) AND a JSON-stringified text block in `content` for compatibility.
   *
   * The MCP spec marks `content` as optional when `structuredContent` is
   * provided, but it also says "a tool that returns structured content
   * SHOULD also return the serialized JSON in a TextContent block". 1.1.0
   * shipped without the duplicate and Perplexity surfaced it as an opaque
   * "Error" — restored in 1.1.2 (regression fix).
   */
  protected async wrapStructured<T>(fn: () => Promise<T>) {
    try {
      const data = await fn();
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data) }],
        structuredContent: data as Record<string, unknown>,
      };
    } catch (err) {
      return toolError(err);
    }
  }

  async init() {
    instrumentRegisterTool(this.server);

    // ---------------- profile / identity --------------------------------------
    this.server.registerTool(
      "get_me",
      {
        title: "My profile",
        description:
          "Profile of the authenticated club member (the OAuth-connected user themselves). Returns the same shape as get_user but with private fields (bio, contacts, payment status) populated. Call this once at the start of a session to learn who 'I' am — most other tools take a slug, and `get_me().user.slug` is yours.",
        inputSchema: {},
        outputSchema: userResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async () => this.wrapStructured(() => this.client().getMe()),
    );

    this.server.registerTool(
      "get_user",
      {
        title: "Member profile",
        description:
          "Public profile of a club member identified by URL slug (e.g. 'vas3k' for vas3k.club/user/vas3k/). Use search_users to discover slugs from a name prefix. Private fields (bio, location) are only populated when the OAuth grant covers the `contact` scope; missing fields are absent rather than null.",
        inputSchema: { slug: SLUG },
        outputSchema: userResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ slug }) => this.wrapStructured(() => this.client().getUser(slug)),
    );

    this.server.registerTool(
      "get_user_tags",
      {
        title: "Member profile tags",
        description:
          "Topical tags on a member's profile, grouped by category (`tech`, `hobbies`, `personal`, `club`, `collectible`, `other`). Use these to learn what someone works with or is interested in. Empty groups are omitted from the response.",
        inputSchema: { slug: SLUG },
        outputSchema: userTagsResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ slug }) => this.wrapStructured(() => this.client().getUserTags(slug)),
    );

    this.server.registerTool(
      "get_user_badges",
      {
        title: "Member badges (peer-awarded)",
        description:
          "Badges other members have given this user. Each entry includes the badge metadata, the giver's profile (`from_user`), an optional note, and an optional link to the post or comment the badge was awarded on. Note: upstream has a known FieldError on `/user/<slug>/badges.json` as of 2026-04 — the call may 400 until vas3k.club lands the fix.",
        inputSchema: { slug: SLUG },
        outputSchema: userBadgesResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ slug }) => this.wrapStructured(() => this.client().getUserBadges(slug)),
    );

    this.server.registerTool(
      "get_user_achievements",
      {
        title: "Member achievements",
        description:
          "Activity-based achievements the member has earned (e.g. anniversary, post-of-the-week winner). Different from badges — achievements are awarded by the platform, badges are awarded by other members. Ordered most-recent first.",
        inputSchema: { slug: SLUG },
        outputSchema: userAchievementsResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ slug }) => this.wrapStructured(() => this.client().getUserAchievements(slug)),
    );

    this.server.registerTool(
      "find_user_by_telegram",
      {
        title: "Find member by Telegram id",
        description:
          "Look up a club member by their numeric Telegram user id (NOT their @username — the integer id from the Telegram API). Useful for bridging a Telegram chat handle to a vas3k.club profile. Returns the same shape as get_user; 404 if no member has linked that id.",
        inputSchema: {
          telegram_id: z
            .union([z.string(), z.number().int()])
            .transform(String)
            .describe("Numeric Telegram user id, e.g. 12345678. Strings are coerced."),
        },
        outputSchema: userResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ telegram_id }) =>
        this.wrapStructured(() => this.client().findUserByTelegram(telegram_id)),
    );

    // ---------------- posts ---------------------------------------------------
    this.server.registerTool(
      "get_post",
      {
        title: "Post (JSON)",
        description:
          "Fetch a post by its type and slug. Returns the JSON Feed 1.1 entry shape — `content_text` holds the plain-text body, `_club` carries vas3k-specific metadata (upvotes, view count, comment_count). Most posts come from get_feed where each item already includes both `_club.type` and `_club.slug` ready to pass back here. If you don't know the type, get_feed is more forgiving than guessing.",
        inputSchema: { post_type: POST_TYPE, slug: SLUG },
        outputSchema: postResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ post_type, slug }) =>
        this.wrapStructured(() => this.client().getPost(post_type, slug)),
    );

    this.server.registerTool(
      "get_post_markdown",
      {
        title: "Post body (raw Markdown)",
        description:
          "Raw Markdown body of a post. Prefer this over get_post when you want to QUOTE the post in a reply or summary — get_post returns plain-text with formatting flattened. Returns the literal '🔒' for non-public posts the OAuth user can't see.",
        inputSchema: { post_type: POST_TYPE, slug: SLUG },
        annotations: READ_ANNOTATIONS,
      },
      async ({ post_type, slug }) =>
        this.wrap(() => this.client().getPostMarkdown(post_type, slug)),
    );

    this.server.registerTool(
      "list_post_comments",
      {
        title: "Post comments",
        description:
          "All visible comments on a post, ordered oldest-first. Each comment has an `id` (UUID, used by upvote_comment / retract_comment_vote on /mcp-full), a `reply_to_id` (parent UUID for threaded replies, or null for top-level), the author's full profile, upvote count, and timestamp. Combine with get_post_markdown to summarize a discussion.",
        inputSchema: { post_type: POST_TYPE, slug: SLUG },
        outputSchema: commentsResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ post_type, slug }) =>
        this.wrapStructured(() => this.client().listPostComments(post_type, slug)),
    );

    // ---------------- feeds ---------------------------------------------------
    this.server.registerTool(
      "get_feed",
      {
        title: "Feed page",
        description:
          "One page of the public feed in JSON Feed 1.1 format. Default arguments give the global activity feed — same view a logged-in member sees on the homepage. To browse a specific topic use post_type='project' (or any other type) and ordering='top_week' / 'hot'. Pages start at 1; `next_url` in the response indicates more pages exist. Per-item `content_text` is truncated to a preview (~1000 chars) when the post is longer; truncated items carry `_club.content_truncated:true`, `_club.content_full_chars:<N>`, AND a `[Truncated preview — N of M chars shown. Full body via get_post(post_type=\"…\", slug=\"…\").]` suffix in the text itself — so you always know when you're looking at a preview and exactly which call returns the full body.",
        inputSchema: {
          post_type: FEED_POST_TYPE,
          ordering: ORDERING.default("activity"),
          page: z
            .number()
            .int()
            .min(1)
            .default(1)
            .describe("1-indexed page number. Each page is roughly 25 items."),
        },
        outputSchema: feedShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ post_type, ordering, page }) =>
        this.wrapStructured(() => this.client().getFeed({ post_type, ordering, page })),
    );

    // ---------------- search --------------------------------------------------
    this.server.registerTool(
      "search_users",
      {
        title: "Search members by slug prefix",
        description:
          "Find members whose URL slug starts with the given prefix. Returns up to 5 minimal records (`slug` + `full_name`) — call get_user with the slug to get the full profile. Note: matches the slug, NOT the full name. If the user is named 'Alex Smith' but their slug is 'alex_s', you must search 'alex' or 'alex_s', not 'smith'.",
        inputSchema: {
          prefix: z
            .string()
            .min(3)
            .max(15)
            .describe("Slug prefix, 3–15 chars. Shorter prefixes return 400."),
        },
        outputSchema: searchUsersResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ prefix }) => this.wrapStructured(() => this.client().searchUsers(prefix)),
    );

    this.server.registerTool(
      "search_tags",
      {
        title: "Search profile tags",
        description:
          "Search the topical-tag taxonomy. Without filters returns the full list (handy to learn what tag groups exist). With `prefix` returns matching codes; with `group` narrows to one category. Use this to look up the canonical tag code before calling toggle_profile_tag, or to discover related tags around a topic.",
        inputSchema: {
          prefix: z
            .string()
            .min(3)
            .max(15)
            .optional()
            .describe("Optional tag-code prefix, 3–15 chars."),
          group: TAG_GROUP.optional(),
        },
        outputSchema: searchTagsResponseShape,
        annotations: READ_ANNOTATIONS,
      },
      async ({ prefix, group }) =>
        this.wrapStructured(() => this.client().searchTags({ prefix, group })),
    );

    // ---------------- resources ----------------------------------------------
    // Resources let MCP-aware clients surface "always-available" context to
    // the model without burning a tool call. We expose the authenticated
    // user's profile as `vas3k://me` and a server-capability cheatsheet as
    // `vas3k://about`. Both are cheap fetches; clients usually fetch on
    // session start.
    this.server.registerResource(
      "me",
      "vas3k://me",
      {
        title: "My profile",
        description:
          "Live profile of the authenticated member. Same payload as the get_me tool; surfaced as a resource so MCP clients can pin it as ambient session context.",
        mimeType: "application/json",
      },
      async (uri) => {
        const data = await this.client().getMe();
        return {
          contents: [
            {
              uri: uri.href,
              mimeType: "application/json",
              text: JSON.stringify(data),
            },
          ],
        };
      },
    );

    this.server.registerResource(
      "about",
      "vas3k://about",
      {
        title: "Server capabilities",
        description:
          "Human-readable cheatsheet describing this MCP server's tools, naming conventions, and common workflows. Same content the install guide at https://vas3k-mcp.rmbk.me/install.md surfaces.",
        mimeType: "text/markdown",
      },
      async (uri) => ({
        contents: [
          {
            uri: uri.href,
            mimeType: "text/markdown",
            text: ABOUT_MARKDOWN,
          },
        ],
      }),
    );

    // ---------------- prompts -------------------------------------------------
    // One starter prompt: a guided "what happened this week" digest. Clients
    // expose registered prompts in their slash-command UI, so this becomes
    // available as e.g. `/vas3k/weekly_digest` in Claude Desktop.
    this.server.registerPrompt(
      "weekly_digest",
      {
        title: "Weekly digest",
        description:
          "Build a short digest of what happened in vas3k.club over the last week. Picks an ordering, walks the feed, then summarizes by theme.",
        argsSchema: {
          post_type: z
            .enum(["all", ...POST_TYPE_VALUES])
            .optional()
            .describe("Filter the digest to a single post type (default: all)."),
          focus: z
            .string()
            .optional()
            .describe("Optional topic focus, e.g. 'AI', 'startups', 'remote work'."),
        },
      },
      ({ post_type, focus }) => {
        const filter = post_type && post_type !== "all" ? `, type=${post_type}` : "";
        const focusLine = focus ? `\n\nGive extra weight to anything related to: ${focus}.` : "";
        return {
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: `Build a digest of vas3k.club for the past week.

1. Call get_feed(ordering="top_week"${filter}) to pull this week's most upvoted posts.
2. For each interesting item (≥10 upvotes or ≥10 comments), call get_post_markdown to read the body and list_post_comments to see the discussion.
3. Group the digest by theme (tech, life, projects, etc).
4. For each theme: 2–4 bullets, each citing the post URL and the author's slug.
5. Close with one paragraph "vibes" — what the community seemed to care about this week.${focusLine}`,
              },
            },
          ],
        };
      },
    );
  }
}
