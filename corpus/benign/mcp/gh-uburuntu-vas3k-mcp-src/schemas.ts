/**
 * Shared zod schemas for vas3k.club API responses.
 *
 * Single source of truth used at runtime (registered as MCP tool
 * `outputSchema`s, so MCP clients receive rich JSON Schemas + structured
 * content blocks instead of opaque text) AND in contract tests (`test/contract`
 * asserts the live API still matches).
 *
 * Source of truth for upstream shapes:
 *   - users:    reference/users/models/user.py      :: User.to_dict
 *   - posts:    reference/posts/models/post.py      :: Post.to_dict / Post.to_json_feed_entry
 *   - comments: reference/comments/models.py        :: Comment.to_dict
 *   - feed:     reference/posts/api.py              :: api_posts (json_feed)
 *   - tags:     reference/tags/models.py            :: Tag.GROUPS, Tag.to_dict
 *   - badges:   reference/badges/models.py          :: UserBadge.to_dict
 *   - achs:     reference/achievements/models.py    :: UserAchievement.to_dict
 *
 * Design notes
 * ------------
 * Schemas use `z.object` (zod 4 default = "strip"): unknown keys are silently
 * dropped during validation, so a forward-compatible upstream addition does
 * not break the structured-content pipeline at runtime. Removals or type
 * changes still surface — both as a contract-test failure and (in prod) as a
 * tool-call error from the SDK's `validateToolOutput` step.
 *
 * `*ResponseShape` exports are raw shapes (suitable for the SDK's
 * `outputSchema` parameter, which wraps them with `z.object`).
 * `*ResponseSchema` exports are the wrapped objects (suitable for `parse()`
 * in tests).
 */

import { z } from "zod";

// ---------- canonical enum values ----------

/** Mirrors `Tag.GROUPS` (reference/tags/models.py:17-24). */
export const TAG_GROUP_VALUES = [
  "club",
  "tech",
  "hobbies",
  "personal",
  "collectible",
  "other",
] as const;

/** Mirrors `Post.TYPES` (reference/posts/models/post.py:24-49). */
export const POST_TYPE_VALUES = [
  "post",
  "intro",
  "link",
  "question",
  "idea",
  "project",
  "event",
  "battle",
  "weekly_digest",
  "guide",
  "thread",
  "docs",
] as const;

/** Mirrors the URL patterns under `posts/urls.py` for `<ordering>/feed.json`. */
export const ORDERING_VALUES = [
  "activity",
  "new",
  "top",
  "top_week",
  "top_month",
  "top_year",
  "hot",
] as const;

// ---------- user ----------

export const userSchema = z.object({
  id: z.uuid().describe("Stable user UUID"),
  slug: z.string().describe("URL handle, e.g. 'vas3k' — usable in get_user, friend toggle, etc."),
  full_name: z.string().describe("Display name as the user wrote it on their profile"),
  avatar: z.string().nullable().describe("Avatar image URL, or null if the user has none"),
  upvotes: z
    .number()
    .int()
    .describe("Lifetime upvotes the user has received on posts and comments"),
  created_at: z.string().describe("ISO-8601 timestamp of account creation"),
  membership_started_at: z.string().describe("ISO-8601 timestamp"),
  membership_expires_at: z.string().describe("ISO-8601 timestamp"),
  moderation_status: z
    .string()
    .describe("'intro' | 'on_review' | 'rejected' | 'approved' | 'deleted'"),
  payment_status: z.string().describe("'active' | 'inactive'"),
  is_active_member: z.boolean().describe("True iff the membership has not lapsed"),
  // Private fields — only emitted when the OAuth token has the `contact` scope
  // (reference/users/api.py:30-32). For other users without that scope, these
  // fields are missing rather than null.
  bio: z.string().nullable().optional().describe("Free-form bio markdown"),
  company: z.string().nullable().optional(),
  position: z.string().nullable().optional(),
  city: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
});

export const userResponseShape = { user: userSchema };
export const userResponseSchema = z.object(userResponseShape);

// ---------- user/<slug>/tags ----------

export const userTagsResponseShape = {
  tags: z
    .partialRecord(
      z.enum(TAG_GROUP_VALUES),
      z.array(z.object({ code: z.string(), name: z.string() })),
    )
    .describe("Tags grouped by category. Keys are tag groups; empty groups are omitted."),
};
export const userTagsResponseSchema = z.object(userTagsResponseShape);

// ---------- user/<slug>/badges ----------

export const userBadgeSchema = z.object({
  badge: z.object({
    code: z.string(),
    title: z.string(),
    description: z.string().nullable().optional(),
    created_at: z.string(),
  }),
  from_user: userSchema.describe("The member who awarded the badge"),
  created_at: z.string().describe("ISO-8601 timestamp of when the badge was given"),
  post: z.object({ id: z.string() }).nullable().optional(),
  comment: z.object({ id: z.string() }).nullable().optional(),
  note: z.string().nullable().optional().describe("Optional note left by the giver"),
});

export const userBadgesResponseShape = { user_badges: z.array(userBadgeSchema) };
export const userBadgesResponseSchema = z.object(userBadgesResponseShape);

// ---------- user/<slug>/achievements ----------

export const userAchievementSchema = z.object({
  achievement: z.object({
    code: z.string(),
    name: z.string(),
    image: z.string().nullable().optional(),
    description: z.string().nullable().optional(),
    style: z.string().nullable().optional(),
  }),
  created_at: z.string().describe("ISO-8601 timestamp of when the achievement was earned"),
});

export const userAchievementsResponseShape = {
  user_achievements: z.array(userAchievementSchema),
};
export const userAchievementsResponseSchema = z.object(userAchievementsResponseShape);

// ---------- post (single) and feed item (JSON Feed 1.1 entry) ----------

export const postItemSchema = z.object({
  id: z.string().describe("JSON Feed entry id (post URL)"),
  url: z.url(),
  title: z.string(),
  content_text: z
    .string()
    .describe("Plain-text content. Returns the literal '🔒' for non-public posts."),
  date_published: z.string().nullable(),
  date_modified: z.string().nullable(),
  authors: z.array(
    z.object({
      name: z.string(),
      url: z.url(),
      avatar: z.string().nullable(),
    }),
  ),
  _club: z
    .object({
      type: z.string().describe("Post type — one of POST_TYPE_VALUES"),
      slug: z.string().describe("URL slug — pass back into get_post / list_post_comments"),
      coauthors: z.array(z.string()).optional(),
      comment_count: z.number().int(),
      view_count: z.number().int(),
      upvotes: z.number().int(),
      is_public: z.boolean(),
      is_commentable: z.boolean(),
      // Truncation markers — added by this MCP server's post-processing on
      // feed responses (NOT by upstream `Post.to_json_feed_entry`). Absent
      // when content_text holds the full body.
      content_truncated: z
        .boolean()
        .optional()
        .describe(
          "True if content_text was truncated to a preview by this MCP server. Call get_post(_club.type, _club.slug) for the full body.",
        ),
      content_full_chars: z
        .number()
        .int()
        .optional()
        .describe(
          "Original character count of content_text before truncation. Absent when content_text is the full body.",
        ),
    })
    .describe("vas3k.club extension to JSON Feed 1.1 — extra metadata not in the standard"),
});

export const postResponseShape = { post: postItemSchema };
export const postResponseSchema = z.object(postResponseShape);

// ---------- comments ----------

export const commentSchema = z.object({
  id: z.string().describe("Comment UUID — pass to upvote_comment / retract_comment_vote"),
  url: z.url(),
  text: z.string(),
  author: userSchema,
  reply_to_id: z.string().nullable().describe("Parent comment UUID, or null if top-level"),
  upvotes: z.number().int(),
  created_at: z.string(),
});

export const commentsResponseShape = { comments: z.array(commentSchema) };
export const commentsResponseSchema = z.object(commentsResponseShape);

// ---------- feed (JSON Feed 1.1) ----------
// Upstream emits `next_url` whenever pagination is meaningful
// (reference/posts/api.py:65-74). Declared optional so the last page validates.

export const feedShape = {
  version: z.string().describe("JSON Feed 1.1 version URI"),
  title: z.string(),
  home_page_url: z.url(),
  feed_url: z.url(),
  next_url: z.url().optional().describe("URL of the next page; absent on the last page"),
  items: z.array(postItemSchema),
};
export const feedSchema = z.object(feedShape);

// ---------- search ----------

export const searchUsersResponseShape = {
  users: z
    .array(z.object({ slug: z.string(), full_name: z.string() }))
    .describe("Up to 5 matches; sorted by registration recency"),
};
export const searchUsersResponseSchema = z.object(searchUsersResponseShape);

// `looseObject` keeps the contract test forward-compatible if upstream adds
// a field (the structured-content branch likewise tolerates extras).
export const searchTagsResponseShape = {
  tags: z.array(
    z.looseObject({
      code: z.string().describe("Tag handle, e.g. 'rust' — pass to toggle_profile_tag"),
      group: z.string().describe("One of TAG_GROUP_VALUES"),
      name: z.string(),
      color: z.string().describe("Hex/CSS color computed from the tag code"),
    }),
  ),
};
export const searchTagsResponseSchema = z.object(searchTagsResponseShape);

// ---------- write-action response shapes ----------

/**
 * Shape returned by every plain toggle endpoint: bookmark, post subscription,
 * event participation, friend, room subscribe/mute. Upstream uses
 * `get_or_create() / .delete()` so `created` means the toggle was switched ON
 * by this call, `deleted` means it was switched OFF.
 */
export const toggleActionShape = {
  status: z
    .enum(["created", "deleted"])
    .describe("'created' = the toggle is now ON. 'deleted' = the toggle is now OFF."),
};
export const toggleActionResponseSchema = z.object(toggleActionShape);

/** Shape returned by upvote_post. */
export const postUpvoteResponseShape = {
  post: z.object({
    upvotes: z.number().int().describe("Total upvotes after this call"),
  }),
  upvoted_timestamp: z
    .number()
    .int()
    .describe("Epoch milliseconds of the upvote, or 0 if the call was a no-op"),
};
export const postUpvoteResponseSchema = z.object(postUpvoteResponseShape);

/** Shape returned by retract_post_vote. */
export const postRetractResponseShape = {
  success: z.boolean().describe("False if there was no vote to retract"),
  post: z.object({ upvotes: z.number().int() }),
};
export const postRetractResponseSchema = z.object(postRetractResponseShape);

/** Shape returned by upvote_comment. */
export const commentUpvoteResponseShape = {
  comment: z.object({ upvotes: z.number().int() }),
  upvoted_timestamp: z.number().int(),
};
export const commentUpvoteResponseSchema = z.object(commentUpvoteResponseShape);

/** Shape returned by retract_comment_vote. */
export const commentRetractResponseShape = {
  success: z.boolean(),
  comment: z.object({ upvotes: z.number().int() }),
};
export const commentRetractResponseSchema = z.object(commentRetractResponseShape);

/** Shape returned by toggle_profile_tag — toggle status PLUS the affected tag. */
export const profileTagActionResponseShape = {
  status: z.enum(["created", "deleted"]),
  tag: z.object({
    code: z.string(),
    name: z.string(),
    color: z.string(),
  }),
};
export const profileTagActionResponseSchema = z.object(profileTagActionResponseShape);
