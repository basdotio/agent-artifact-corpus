/**
 * instagram_scraper — Scrape Instagram profiles, hashtags, and search.
 *
 * 3 modes via `source_type`:
 *   profile  → Apify apify/instagram-profile-scraper (public profiles)
 *   hashtag  → Apify apify/instagram-hashtag-scraper (hashtag posts)
 *   search   → Apify apify/instagram-scraper (keyword search)
 *
 * Provider: Apify (needs APIFY_API_TOKEN)
 */

import { z } from "zod";
import type { ToolDefinition } from "../../lib/tool-registry.js";
import { runActor, requireApifyToken } from "../../lib/apify.js";

// ── Types ──────────────────────────────────────────────────

interface IGPost {
  text: string;
  url: string;
  author: string;
  timestamp: string;
  likes: number;
  comments: number;
  shares: number;
  views: number;
  type: "image" | "video" | "carousel" | "reel" | "story";
  media_url: string;
  hashtags: string[];
  source_type: string;
}

// ── Normalize Apify output ─────────────────────────────────

function normalizePost(item: any, sourceType: string): IGPost {
  const caption = item.caption || item.text || item.alt || "";
  const hashtags = (caption.match(/#[\w\u00C0-\u024F]+/g) || []).map((h: string) => h.toLowerCase());

  // Detect content type
  let type: IGPost["type"] = "image";
  if (item.type === "Video" || item.videoUrl || item.isVideo) type = "video";
  else if (item.type === "Sidecar" || item.childPosts?.length > 1 || item.sidecarMediaCount > 1) type = "carousel";
  if (item.productType === "clips" || item.type === "Clip") type = "reel";

  return {
    text: caption,
    url: item.url || item.shortCode ? `https://www.instagram.com/p/${item.shortCode}/` : "",
    author: item.ownerUsername || item.ownerFullName || item.owner?.username || "unknown",
    timestamp: item.timestamp || item.takenAtTimestamp
      ? new Date((item.timestamp || item.takenAtTimestamp) * 1000).toISOString()
      : item.date || "",
    likes: item.likesCount || item.likes || 0,
    comments: item.commentsCount || item.comments || 0,
    shares: 0, // IG API doesn't expose shares
    views: item.videoViewCount || item.videoPlayCount || item.playCount || 0,
    type,
    media_url: item.displayUrl || item.thumbnailUrl || item.imageUrl || "",
    hashtags,
    source_type: sourceType,
  };
}

// ── Mode handlers ──────────────────────────────────────────

async function scrapeProfiles(usernames: string[], maxPosts: number): Promise<IGPost[]> {
  requireApifyToken();

  const input = {
    usernames,
    resultsLimit: maxPosts,
    resultsType: "posts" as const,
  };

  const result = await runActor("apify/instagram-profile-scraper", input);
  if (result.error) throw new Error(result.error);

  return result.items.map((item: any) => normalizePost(item, "profile"));
}

async function scrapeHashtags(hashtags: string[], maxPosts: number): Promise<IGPost[]> {
  requireApifyToken();

  // Clean hashtag input (remove # if present)
  const cleanTags = hashtags.map((h) => h.replace(/^#/, ""));

  const input = {
    hashtags: cleanTags,
    resultsLimit: maxPosts,
  };

  const result = await runActor("apify/instagram-hashtag-scraper", input);
  if (result.error) throw new Error(result.error);

  return result.items.map((item: any) => normalizePost(item, "hashtag"));
}

async function searchIG(keywords: string[], maxPosts: number): Promise<IGPost[]> {
  requireApifyToken();

  const input = {
    search: keywords.join(" "),
    searchType: "hashtag" as const, // search by hashtag is the most reliable
    resultsLimit: maxPosts,
  };

  const result = await runActor("apify/instagram-scraper", input);
  if (result.error) throw new Error(result.error);

  return result.items.map((item: any) => normalizePost(item, "search"));
}

// ── Formatter ──────────────────────────────────────────────

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatPosts(posts: IGPost[], sourceType: string): string {
  if (posts.length === 0) return `No Instagram results found (source_type: ${sourceType})`;

  const header = `## Instagram ${sourceType} results — ${posts.length} posts\n`;

  const lines = posts.map((p, i) => {
    const typeIcon = { image: "🖼", video: "🎬", carousel: "📸", reel: "🎞", story: "📱" }[p.type];
    const engagement = [
      `♥ ${formatNumber(p.likes)}`,
      `💬 ${formatNumber(p.comments)}`,
      p.views > 0 ? `▶ ${formatNumber(p.views)}` : "",
    ].filter(Boolean).join(" ");

    const score = p.likes + p.comments * 3 + p.views * 0.01;
    const textPreview = p.text.slice(0, 300).replace(/\n/g, " ");
    const tags = p.hashtags.slice(0, 5).join(" ");

    return [
      `### ${i + 1}. @${p.author} ${typeIcon} ${engagement} (score:${Math.round(score)})`,
      `> ${textPreview}${p.text.length > 300 ? "..." : ""}`,
      tags ? `> Tags: ${tags}` : "",
      `🔗 ${p.url}`,
      `📅 ${p.timestamp}`,
    ].filter(Boolean).join("\n");
  });

  // Append raw JSON for piping to content_analyzer
  const jsonData = posts.map((p) => ({
    text: p.text,
    author: p.author,
    url: p.url,
    timestamp: p.timestamp,
    reactions: p.likes,
    comments: p.comments,
    shares: p.shares,
    views: p.views,
    content_type: p.type,
    hashtags: p.hashtags,
    source_type: p.source_type,
    platform: "instagram",
  }));

  return header + "\n" + lines.join("\n\n") + "\n\n---\n\n<json>\n" + JSON.stringify(jsonData, null, 2) + "\n</json>";
}

// ── Main execute ───────────────────────────────────────────

async function execute(params: Record<string, any>): Promise<string> {
  const sourceType = params.source_type as string;
  const targets = (params.targets as string).split(",").map((t: string) => t.trim()).filter(Boolean);
  const maxPosts = (params.max_posts as number) || 30;

  let posts: IGPost[];

  switch (sourceType) {
    case "profile":
      posts = await scrapeProfiles(targets, maxPosts);
      break;
    case "hashtag":
      posts = await scrapeHashtags(targets, maxPosts);
      break;
    case "search":
      posts = await searchIG(targets, maxPosts);
      break;
    default:
      return `Unknown source_type: ${sourceType}. Use: profile, hashtag, or search`;
  }

  // Sort by engagement score
  posts.sort((a, b) => {
    const scoreA = a.likes + a.comments * 3 + a.views * 0.01;
    const scoreB = b.likes + b.comments * 3 + b.views * 0.01;
    return scoreB - scoreA;
  });

  return formatPosts(posts.slice(0, maxPosts), sourceType);
}

// ── Tool definition ────────────────────────────────────────

export const definition: ToolDefinition = {
  name: "instagram_scraper",
  description: [
    "Scrape Instagram content from profiles, hashtags, or search.",
    "Modes: profile (user posts + reels), hashtag (hashtag feed), search (keyword search).",
    "Returns posts with likes, comments, views, content type (image/video/carousel/reel), and hashtags.",
    "Output includes JSON for piping to content_scorer or content_analyzer.",
  ].join(" "),
  params: {
    source_type: z
      .enum(["profile", "hashtag", "search"])
      .describe("What to scrape: profile (user posts), hashtag (hashtag feed), search (keyword)"),
    targets: z
      .string()
      .describe(
        "Comma-separated targets. For profile: usernames (without @). For hashtag: hashtag names (with or without #). For search: keywords."
      ),
    max_posts: z.number().min(1).max(200).default(30).describe("Max posts to return (1-200)"),
  },
  envVars: ["APIFY_API_TOKEN"],
  execute,
};
