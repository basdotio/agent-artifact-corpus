/**
 * Read+write variant of the MCP server. Mounted at `/mcp-full`. Inherits the
 * read tools from `MyMCP` and adds write tools that mutate the user's
 * vas3k.club account.
 *
 * Why a separate class / endpoint instead of a global flag:
 *   - Users decide read-vs-read+write at MCP-client-config time (which URL
 *     they paste into Claude Desktop / Cursor), not at deploy time.
 *   - The consent screen at `/authorize` clearly tells the user that this
 *     particular MCP-client wants to use the *full* endpoint (the URL is
 *     surfaced verbatim).
 *
 * Defence in depth: every write tool also goes through `writeClient()`,
 * which 403s when the granted MCP-side scope set doesn't include `write`.
 * Today most MCP clients request the full set by default, so the check is
 * usually a no-op — but a security-conscious client (or future tightening
 * of the consent UI) can drop `write` and the boundary holds.
 *
 * Write coverage: only the cleanly @api-decorated POST views from upstream
 * (votes, bookmarks, subscriptions, friend, mute, room subscribe/mute,
 * profile-tag toggle). The form-based ones (`create_comment`, `edit_post`,
 * `delete_post`, badge/payment) return HTML+redirects, so wrapping them
 * needs more plumbing — left for a future pass.
 *
 * Tool annotation taxonomy
 * ------------------------
 * Every write tool sets all four standard hints. Three buckets cover the
 * surface — pick the constant that matches the tool's semantics:
 *
 *   ADDITIVE_IDEMPOTENT  — pure setter, never removes data.
 *                          Examples: upvote_post, upvote_comment.
 *                          { readOnlyHint:false, destructiveHint:false,
 *                            idempotentHint:true,  openWorldHint:true }
 *
 *   DESTRUCTIVE_IDEMPOTENT — pure remover, takes data away but re-running
 *                            with the same args has no extra effect.
 *                          Examples: retract_post_vote, retract_comment_vote.
 *                          { readOnlyHint:false, destructiveHint:true,
 *                            idempotentHint:true,  openWorldHint:true }
 *
 *   TOGGLE               — flips state each call; the off-direction call
 *                          removes prior state, so destructiveHint is true
 *                          and idempotentHint is false.
 *                          Examples: bookmark_post, toggle_friend,
 *                          subscribe_room, mute_room, toggle_profile_tag,
 *                          toggle_post_subscription, toggle_event_participation.
 *                          { readOnlyHint:false, destructiveHint:true,
 *                            idempotentHint:false, openWorldHint:true }
 *
 * `openWorldHint:true` everywhere — we always reach an external service.
 * Per the spec, a careful client uses `destructiveHint` to decide whether
 * to confirm before calling, and `idempotentHint` to decide whether retry
 * is safe.
 */

import { z } from "zod";

import { MyMCP } from "./mcp";
import {
  commentRetractResponseShape,
  commentUpvoteResponseShape,
  postRetractResponseShape,
  postUpvoteResponseShape,
  profileTagActionResponseShape,
  toggleActionShape,
} from "./schemas";
import { Vas3kAPIError } from "./vas3k-client";

const COMMENT_ID = z
  .uuid()
  .describe("Comment UUID — get it from the `id` field of any item in `list_post_comments`.");

const POST_SLUG = z
  .string()
  .describe(
    "Post URL slug (the trailing path segment, e.g. 'my-post' for vas3k.club/post/my-post/).",
  );

const ROOM_SLUG = z
  .string()
  .describe("Room slug (e.g. 'ai', 'apps', 'remote'). Browse vas3k.club/rooms/ for the full list.");

const USER_SLUG = z.string().describe("Member URL slug (the handle from search_users / get_user).");

const TAG_CODE = z
  .string()
  .describe(
    "Tag code from search_tags (e.g. 'rust', 'kyiv'). NOT the human-readable name — use search_tags to find the canonical code.",
  );

/** Pure setter, never removes data — e.g. upvote_post. */
const ADDITIVE_IDEMPOTENT_ANNOTATIONS = {
  readOnlyHint: false,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: true,
} as const;

/** Pure remover, idempotent — e.g. retract_post_vote. */
const DESTRUCTIVE_IDEMPOTENT_ANNOTATIONS = {
  readOnlyHint: false,
  destructiveHint: true,
  idempotentHint: true,
  openWorldHint: true,
} as const;

/** Toggle — flips state each call; the off path removes prior state. */
const TOGGLE_ANNOTATIONS = {
  readOnlyHint: false,
  destructiveHint: true,
  idempotentHint: false,
  openWorldHint: true,
} as const;

export class MyMCPFull extends MyMCP {
  // Intentionally do NOT redeclare `server` — inherit the parent's instance
  // so super.init()'s registrations and ours land on the same McpServer.

  /**
   * Like `client()`, but additionally enforces that the current session was
   * granted the `write` MCP-side scope. Use this from every write-tool
   * handler instead of `client()`. Today most MCP clients request the full
   * scope set so the check is a no-op for them — but a security-conscious
   * client (or future tightening of the consent UI) can drop `write` and
   * the boundary will hold.
   */
  protected writeClient(): ReturnType<MyMCP["client"]> {
    const scopes = this.props?.mcpScopes;
    if (!scopes?.includes("write")) {
      throw new Vas3kAPIError(403, {
        error: "missing_scope",
        error_description: "this tool requires the `write` MCP scope",
      });
    }
    return this.client();
  }

  async init() {
    // Inherit all read tools first.
    await super.init();

    // ---------------- post-level write actions ------------------------------
    this.server.registerTool(
      "bookmark_post",
      {
        title: "Bookmark post (toggle)",
        description:
          "Add this post to the user's bookmarks, or remove it if it was already bookmarked. Same call performs both — there is no separate `unbookmark_post`. Response.status is 'created' if it's now bookmarked, 'deleted' if the bookmark was just removed.",
        inputSchema: { post_slug: POST_SLUG },
        outputSchema: toggleActionShape,
        annotations: TOGGLE_ANNOTATIONS,
      },
      async ({ post_slug }) =>
        this.wrapStructured(() => this.writeClient().bookmarkPost(post_slug)),
    );

    this.server.registerTool(
      "upvote_post",
      {
        title: "Upvote post",
        description:
          "Upvote a post. Idempotent — calling twice does NOT downvote (use retract_post_vote for that). Returns the new total upvote count plus the upvote timestamp.",
        inputSchema: { post_slug: POST_SLUG },
        outputSchema: postUpvoteResponseShape,
        annotations: ADDITIVE_IDEMPOTENT_ANNOTATIONS,
      },
      async ({ post_slug }) => this.wrapStructured(() => this.writeClient().upvotePost(post_slug)),
    );

    this.server.registerTool(
      "retract_post_vote",
      {
        title: "Retract post upvote",
        description:
          "Retract the user's upvote on a post. Idempotent — `success:false` in the response means there was no vote to retract; `success:true` means a vote was removed and the upvote count decremented.",
        inputSchema: { post_slug: POST_SLUG },
        outputSchema: postRetractResponseShape,
        annotations: DESTRUCTIVE_IDEMPOTENT_ANNOTATIONS,
      },
      async ({ post_slug }) =>
        this.wrapStructured(() => this.writeClient().retractPostVote(post_slug)),
    );

    this.server.registerTool(
      "toggle_post_subscription",
      {
        title: "Subscribe to post comments (toggle)",
        description:
          "Subscribe to email + Telegram notifications for new top-level comments on this post, or unsubscribe if already subscribed. Response.status='created' means now subscribed.",
        inputSchema: { post_slug: POST_SLUG },
        outputSchema: toggleActionShape,
        annotations: TOGGLE_ANNOTATIONS,
      },
      async ({ post_slug }) =>
        this.wrapStructured(() => this.writeClient().togglePostSubscription(post_slug)),
    );

    this.server.registerTool(
      "toggle_event_participation",
      {
        title: "RSVP to event (toggle)",
        description:
          "For posts of type `event`: mark the authenticated user as participating, or unmark them if already RSVPed. Also auto-subscribes them to the event's comments. Response.status='created' = now attending. Calling on a non-event post may fail.",
        inputSchema: { post_slug: POST_SLUG },
        outputSchema: toggleActionShape,
        annotations: TOGGLE_ANNOTATIONS,
      },
      async ({ post_slug }) =>
        this.wrapStructured(() => this.writeClient().toggleEventParticipation(post_slug)),
    );

    // ---------------- comment-level write actions ---------------------------
    this.server.registerTool(
      "upvote_comment",
      {
        title: "Upvote comment",
        description:
          "Upvote a comment by its UUID. Idempotent (re-calls don't double-count). Get the comment_id from `list_post_comments`.",
        inputSchema: { comment_id: COMMENT_ID },
        outputSchema: commentUpvoteResponseShape,
        annotations: ADDITIVE_IDEMPOTENT_ANNOTATIONS,
      },
      async ({ comment_id }) =>
        this.wrapStructured(() => this.writeClient().upvoteComment(comment_id)),
    );

    this.server.registerTool(
      "retract_comment_vote",
      {
        title: "Retract comment upvote",
        description:
          "Retract the user's upvote on a comment. Idempotent — `success:false` if there was no vote to retract.",
        inputSchema: { comment_id: COMMENT_ID },
        outputSchema: commentRetractResponseShape,
        annotations: DESTRUCTIVE_IDEMPOTENT_ANNOTATIONS,
      },
      async ({ comment_id }) =>
        this.wrapStructured(() => this.writeClient().retractCommentVote(comment_id)),
    );

    // ---------------- social write actions ----------------------------------
    this.server.registerTool(
      "toggle_friend",
      {
        title: "Friend request (toggle)",
        description:
          "Send a friend request to another member, or revoke a pending/accepted request. Response.status='created' means a request was just sent (or accepted, if mutual); 'deleted' means the existing relation was removed. Cannot friend yourself (400).",
        inputSchema: { user_slug: USER_SLUG },
        outputSchema: toggleActionShape,
        annotations: TOGGLE_ANNOTATIONS,
      },
      async ({ user_slug }) =>
        this.wrapStructured(() => this.writeClient().toggleFriend(user_slug)),
    );

    // toggle_mute_user is intentionally absent — see Vas3kClient comment:
    // upstream `users/views/muted.py::toggle_mute` is HTML+email-only,
    // not API-shaped, so a Bearer-authed call always 500s.

    // ---------------- rooms -------------------------------------------------
    this.server.registerTool(
      "subscribe_room",
      {
        title: "Subscribe to room (toggle)",
        description:
          "Toggle subscription to a room (e.g. `ai`, `apps`, `remote`). Subscribed rooms appear in the user's email digest and are easier to find in the feed. Distinct from mute_room — a room can be subscribed AND not muted, neither, or both.",
        inputSchema: { room_slug: ROOM_SLUG },
        outputSchema: toggleActionShape,
        annotations: TOGGLE_ANNOTATIONS,
      },
      async ({ room_slug }) =>
        this.wrapStructured(() => this.writeClient().subscribeRoom(room_slug)),
    );

    this.server.registerTool(
      "mute_room",
      {
        title: "Mute room (toggle)",
        description:
          "Toggle muting a room. Muted rooms don't appear in the main feed and don't generate notifications. Independent from subscribe_room — muting also unsubscribes-by-default for digest purposes, but the two toggles can be set independently.",
        inputSchema: { room_slug: ROOM_SLUG },
        outputSchema: toggleActionShape,
        annotations: TOGGLE_ANNOTATIONS,
      },
      async ({ room_slug }) => this.wrapStructured(() => this.writeClient().muteRoom(room_slug)),
    );

    // ---------------- profile -----------------------------------------------
    this.server.registerTool(
      "toggle_profile_tag",
      {
        title: "Profile tag (toggle)",
        description:
          "Add a topical tag to the authenticated user's profile, or remove it if already present. Use search_tags first to find the canonical tag_code (NOT the display name — codes are lowercase ASCII). Response includes both the new toggle status and the affected tag's full record (code, name, color).",
        inputSchema: { tag_code: TAG_CODE },
        outputSchema: profileTagActionResponseShape,
        annotations: TOGGLE_ANNOTATIONS,
      },
      async ({ tag_code }) =>
        this.wrapStructured(() => this.writeClient().toggleProfileTag(tag_code)),
    );
  }
}
