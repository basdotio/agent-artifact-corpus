/**
 * Tiny `fetch` wrapper for the vas3k.club JSON API. Same surface as the
 * Python `Vas3kClient`, but stateless — every call takes the bearer token
 * we minted during the OAuth dance.
 */

import { UPSTREAM_TIMEOUT_MS, USER_AGENT } from "./constants";

export class Vas3kAPIError extends Error {
  constructor(
    public status: number,
    public payload: unknown,
  ) {
    super(`vas3k.club API ${status}: ${JSON.stringify(payload).slice(0, 200)}`);
    this.name = "Vas3kAPIError";
  }
}

export interface Vas3kClientOptions {
  baseUrl: string;
  /** OAuth2 bearer token. Sent as `Authorization: Bearer <token>`. */
  accessToken?: string;
  /**
   * vas3k.club service token (`st_…`). Sent as `X-Service-Token: <token>` and
   * authenticates as the OAuth app's owner. Used by integration tests that
   * can't easily perform the full OAuth dance; production traffic uses
   * `accessToken` instead.
   */
  serviceToken?: string;
}

const SLUG_RE = /^[a-zA-Z0-9_-]{1,64}$/;
const TELEGRAM_ID_RE = /^\d+$/;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Max characters of `content_text` we keep per item in feed responses.
 * Upstream JSON Feed includes the full markdown body of every post — a default
 * page (70 items × long posts) easily hits 4 MB and blows past Perplexity's
 * tool-result limit (1.1.0 regression caught 2026-04-20). Trim to a preview;
 * agents can call get_post for the full body.
 *
 * 1000 chars ≈ first paragraph — enough signal for the agent to decide
 * whether to drill in. Per-page payload then stays around ~100 KB even on a
 * 70-item page.
 */
export const FEED_PREVIEW_CHARS = 1000;

/**
 * Mutates the feed payload in place: trims each item's `content_text` to a
 * preview AND emits three self-announcing signals so the LLM knows the
 * content was cut and how to retrieve the full body:
 *
 *   1. An in-band suffix in `content_text` itself (visible to any model that
 *      reads the field directly): `…[Truncated preview — N of M chars
 *      shown. Full body via get_post(post_type="…", slug="…").]`
 *   2. `_club.content_truncated: true` — boolean machine flag.
 *   3. `_club.content_full_chars: <original>` — so the agent can decide
 *      whether the missing tail is worth drilling in for.
 *
 * Untruncated items get neither the suffix nor the markers (so absence ⇒
 * full content). Tolerant of unknown shapes — returns input unchanged if
 * the envelope doesn't look like `{items: [...]}`.
 */
function trimFeedItemContent<T>(data: T): T {
  if (!data || typeof data !== "object" || !("items" in data)) return data;
  const items = (data as { items?: unknown[] }).items;
  if (!Array.isArray(items)) return data;
  for (const item of items) {
    if (!item || typeof item !== "object") continue;
    const ct = (item as { content_text?: unknown }).content_text;
    if (typeof ct !== "string" || ct.length <= FEED_PREVIEW_CHARS) continue;

    // Pull the per-post identifiers so the suffix is self-contained — the
    // LLM can copy the exact get_post call without traversing the envelope.
    const club = (item as { _club?: Record<string, unknown> })._club;
    const postType = (club?.type as string | undefined) ?? "post";
    const slug = (club?.slug as string | undefined) ?? "";
    const preview = ct.slice(0, FEED_PREVIEW_CHARS).trimEnd();
    (item as { content_text: string }).content_text =
      `${preview}…\n\n[Truncated preview — ${FEED_PREVIEW_CHARS} of ${ct.length} chars shown. ` +
      `Full body via get_post(post_type="${postType}", slug="${slug}").]`;

    if (club && typeof club === "object") {
      club.content_truncated = true;
      club.content_full_chars = ct.length;
    }
  }
  return data;
}

function assertMatches(value: string, pattern: RegExp, label: string): void {
  if (!pattern.test(value)) throw new Vas3kAPIError(400, { error: `invalid ${label}` });
}
const assertSlug = (slug: string) => assertMatches(slug, SLUG_RE, "slug");
const assertTelegramId = (id: string) => assertMatches(id, TELEGRAM_ID_RE, "telegram id");
const assertUuid = (id: string) => assertMatches(id, UUID_RE, "uuid");

export class Vas3kClient {
  constructor(private readonly opts: Vas3kClientOptions) {}

  private async request<T>(
    path: string,
    init: {
      method?: string;
      params?: Record<string, string | number | undefined>;
      text?: boolean;
    } = {},
  ): Promise<T> {
    const url = new URL(path, this.opts.baseUrl);
    for (const [k, v] of Object.entries(init.params ?? {})) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }

    const headers: Record<string, string> = {
      "User-Agent": USER_AGENT,
    };
    if (this.opts.accessToken) {
      headers.Authorization = `Bearer ${this.opts.accessToken}`;
    } else if (this.opts.serviceToken) {
      headers["X-Service-Token"] = this.opts.serviceToken;
    }

    const response = await fetch(url.toString(), {
      method: init.method ?? "GET",
      headers,
      // Upstream returns 302 → HTML when post type doesn't match the slug
      // (reference/posts/api.py:19-22). Treat 3xx as an error rather than
      // following the redirect into an HTML page.
      redirect: "manual",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });

    if (response.status >= 300 && response.status < 400) {
      throw new Vas3kAPIError(response.status, {
        redirect: response.headers.get("location"),
      });
    }

    if (!response.ok) {
      // Read the body once as text, then opportunistically parse as JSON.
      // The previous `try response.json() / catch response.text()` shape
      // crashes with "Body is unusable" when the body isn't JSON, because
      // `.json()` consumes the body before throwing.
      const body = await response.text();
      let payload: unknown = body;
      try {
        payload = JSON.parse(body);
      } catch {
        // leave payload as the raw text
      }
      throw new Vas3kAPIError(response.status, payload);
    }

    if (init.text) return (await response.text()) as T;
    const ct = response.headers.get("content-type") ?? "";
    if (ct.includes("application/json") || ct.includes("application/feed+json")) {
      return (await response.json()) as T;
    }
    // Non-JSON body on a JSON-typed call site (e.g. an HTML error page from
    // a Cloudflare WAF in front of vas3k.club). Don't return raw text — that
    // would deliver a wall of HTML to the LLM.
    throw new Vas3kAPIError(response.status, await response.text());
  }

  getMe = () => this.request<unknown>("/user/me.json");
  getUser = (slug: string) => {
    assertSlug(slug);
    return this.request<unknown>(`/user/${slug}.json`);
  };
  getUserTags = (slug: string) => {
    assertSlug(slug);
    return this.request<unknown>(`/user/${slug}/tags.json`);
  };
  getUserBadges = (slug: string) => {
    assertSlug(slug);
    return this.request<unknown>(`/user/${slug}/badges.json`);
  };
  getUserAchievements = (slug: string) => {
    assertSlug(slug);
    return this.request<unknown>(`/user/${slug}/achievements.json`);
  };
  findUserByTelegram = (telegramId: string) => {
    assertTelegramId(telegramId);
    return this.request<unknown>(`/user/by_telegram_id/${telegramId}.json`);
  };
  getPost = (postType: string, slug: string) => {
    assertSlug(slug);
    return this.request<unknown>(`/${postType}/${slug}.json`);
  };
  getPostMarkdown = (postType: string, slug: string) => {
    assertSlug(slug);
    return this.request<string>(`/${postType}/${slug}.md`, { text: true });
  };
  listPostComments = (postType: string, slug: string) => {
    assertSlug(slug);
    return this.request<unknown>(`/${postType}/${slug}/comments.json`);
  };
  getFeed = async (params: { post_type?: string; ordering?: string; page?: number } = {}) => {
    const post_type = params.post_type ?? "all";
    const ordering = params.ordering ?? "activity";
    const page = params.page ?? 1;
    const path =
      post_type === "all" && ordering === "activity"
        ? "/feed.json"
        : `/${post_type}/${ordering}/feed.json`;
    const data = await this.request<unknown>(path, { params: { page } });
    return trimFeedItemContent(data);
  };
  searchUsers = (prefix: string) => {
    // Mirror upstream's silent-empty rule (reference/search/api.py:18-21):
    // [3..15] chars or you get nothing back. Surface as a 400 here so the
    // failure is visible instead of an empty {users: []}.
    if (prefix.length < 3 || prefix.length > 15) {
      throw new Vas3kAPIError(400, {
        error: "invalid_prefix",
        error_description: "prefix must be 3-15 characters",
      });
    }
    return this.request<unknown>("/search/users.json", { params: { prefix } });
  };
  searchTags = (params: { prefix?: string; group?: string } = {}) =>
    this.request<unknown>("/search/tags.json", { params });

  // ---- write operations ---------------------------------------------------
  // Each write hits an `@api(require_auth=True) @require_http_methods(['POST'])`
  // view that returns a JSON envelope. We append `?is_ajax=1` so the upstream
  // reliably returns JSON (the `@api` decorator otherwise sniffs the request).
  // vas3k.club ships without `CsrfViewMiddleware`, so Bearer-authed POSTs work
  // without a CSRF token. (Verified in reference/club/settings.py — see
  // commit-time README CI/CD section.)

  private postAction<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "POST", params: { is_ajax: "1" } });
  }

  bookmarkPost = (postSlug: string) => {
    assertSlug(postSlug);
    return this.postAction<unknown>(`/post/${postSlug}/bookmark/`);
  };
  upvotePost = (postSlug: string) => {
    assertSlug(postSlug);
    return this.postAction<unknown>(`/post/${postSlug}/upvote/`);
  };
  retractPostVote = (postSlug: string) => {
    assertSlug(postSlug);
    return this.postAction<unknown>(`/post/${postSlug}/retract_vote/`);
  };
  togglePostSubscription = (postSlug: string) => {
    assertSlug(postSlug);
    return this.postAction<unknown>(`/post/${postSlug}/subscription/`);
  };
  toggleEventParticipation = (postSlug: string) => {
    assertSlug(postSlug);
    return this.postAction<unknown>(`/post/${postSlug}/participate/`);
  };
  upvoteComment = (commentId: string) => {
    assertUuid(commentId);
    return this.postAction<unknown>(`/comment/${commentId}/upvote/`);
  };
  retractCommentVote = (commentId: string) => {
    assertUuid(commentId);
    return this.postAction<unknown>(`/comment/${commentId}/retract_vote/`);
  };
  toggleFriend = (userSlug: string) => {
    assertSlug(userSlug);
    return this.postAction<unknown>(`/user/${userSlug}/friend/`);
  };
  // NOTE: `toggle_mute_user` is intentionally NOT exposed. The upstream view
  // `users/views/muted.py::toggle_mute` is decorated with `@require_auth`
  // (not `@api`), returns HTML, and triggers `notify_admins_on_mute` which
  // does an SMTP send. None of that survives a Bearer-token API call.
  subscribeRoom = (roomSlug: string) => {
    assertSlug(roomSlug);
    return this.postAction<unknown>(`/room/${roomSlug}/subscribe/`);
  };
  muteRoom = (roomSlug: string) => {
    assertSlug(roomSlug);
    return this.postAction<unknown>(`/room/${roomSlug}/mute/`);
  };
  toggleProfileTag = (tagCode: string) => {
    assertSlug(tagCode);
    return this.postAction<unknown>(`/profile/tag/${tagCode}/toggle/`);
  };
}
