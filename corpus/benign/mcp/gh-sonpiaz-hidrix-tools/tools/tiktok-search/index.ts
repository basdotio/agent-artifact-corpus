/**
 * tiktok_search — Search TikTok videos, user profiles, hashtags, and video details.
 *
 * 4 modes via `source_type`:
 *   search       → keyword search (default)
 *   user_posts   → get posts from a specific user
 *   hashtag      → get posts from a hashtag
 *   video_detail → get full details of a specific video
 *
 * Provider: RapidAPI (tiktok-api23)
 */

import { z } from "zod";
import type { ToolDefinition } from "../../lib/tool-registry.js";
import { rapidApiGet, requireEnv } from "../../lib/rapidapi.js";

// ── Types ──────────────────────────────────────────────────

interface TikTokPost {
  id: string;
  author: string;
  author_name: string;
  description: string;
  url: string;
  plays: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  duration: number;
  music: string;
  hashtags: string[];
  create_time: string;
}

// ── Config ─────────────────────────────────────────────────

function getConfig() {
  return {
    baseUrl: "https://tiktok-api23.p.rapidapi.com",
    host: "tiktok-api23.p.rapidapi.com",
    apiKey: requireEnv("RAPIDAPI_KEY"),
  };
}

// ── Normalize video data ───────────────────────────────────

function normalizeVideo(video: any): TikTokPost {
  const v = video.item || video;
  const stats = v.stats || {};
  const author = v.author || {};
  const music = v.music || {};
  const desc = v.desc || "";
  const hashtags = (desc.match(/#[\w\u00C0-\u024F]+/g) || []).map((h: string) => h.toLowerCase());
  // Also extract from challenges/textExtra
  if (v.challenges) {
    for (const c of v.challenges) {
      const tag = `#${c.title}`.toLowerCase();
      if (!hashtags.includes(tag)) hashtags.push(tag);
    }
  }

  return {
    id: v.id || "",
    author: author.uniqueId || author.unique_id || "",
    author_name: author.nickname || "",
    description: desc,
    url: `https://tiktok.com/@${author.uniqueId || author.unique_id || ""}/video/${v.id || ""}`,
    plays: stats.playCount || stats.play_count || 0,
    likes: stats.diggCount || stats.digg_count || stats.likeCount || 0,
    comments: stats.commentCount || stats.comment_count || 0,
    shares: stats.shareCount || stats.share_count || 0,
    saves: stats.collectCount || stats.collect_count || stats.favoriteCount || 0,
    duration: v.video?.duration || v.duration || 0,
    music: music.title ? `${music.title} - ${music.authorName || ""}` : "",
    hashtags,
    create_time: v.createTime ? new Date(v.createTime * 1000).toISOString() : "",
  };
}

// ── Mode: Search ───────────────────────────────────────────

async function searchVideos(keyword: string, count: number): Promise<TikTokPost[]> {
  const config = getConfig();
  const result = await rapidApiGet(config, "api/search/general", { keyword, count });
  if (result.error) throw new Error(result.error);

  const data = result.data as any;
  const items = data?.data || data?.items || [];
  if (!Array.isArray(items)) return [];

  return items
    .filter((item: any) => item.type === 1 || item.item)
    .map(normalizeVideo);
}

// ── Mode: User posts ───────────────────────────────────────

async function getUserPosts(username: string, count: number): Promise<TikTokPost[]> {
  const config = getConfig();

  // First get user info to get secUid
  const userResult = await rapidApiGet(config, "api/user/info", { uniqueId: username });
  if (userResult.error) throw new Error(userResult.error);

  const userData = userResult.data as any;
  const secUid = userData?.userInfo?.user?.secUid || userData?.user?.secUid;
  if (!secUid) throw new Error(`User not found: ${username}`);

  // Then get user posts
  const postsResult = await rapidApiGet(config, "api/user/posts", { secUid, count });
  if (postsResult.error) throw new Error(postsResult.error);

  const postsData = postsResult.data as any;
  const items = postsData?.itemList || postsData?.items || postsData?.data?.itemList || [];
  if (!Array.isArray(items)) return [];

  return items.map(normalizeVideo);
}

// ── Mode: Hashtag ──────────────────────────────────────────

async function getHashtagPosts(hashtag: string, count: number): Promise<TikTokPost[]> {
  const config = getConfig();
  const cleanTag = hashtag.replace(/^#/, "");

  // Get hashtag info first
  const tagResult = await rapidApiGet(config, "api/hashtag/info", { name: cleanTag });
  if (tagResult.error) throw new Error(tagResult.error);

  const tagData = tagResult.data as any;
  const challengeId = tagData?.challengeInfo?.challenge?.id || tagData?.data?.challengeInfo?.challenge?.id;
  if (!challengeId) throw new Error(`Hashtag not found: #${cleanTag}`);

  // Get posts for hashtag
  const postsResult = await rapidApiGet(config, "api/hashtag/posts", { challengeId, count });
  if (postsResult.error) throw new Error(postsResult.error);

  const postsData = postsResult.data as any;
  const items = postsData?.itemList || postsData?.items || postsData?.data?.itemList || [];
  if (!Array.isArray(items)) return [];

  return items.map(normalizeVideo);
}

// ── Mode: Video detail ─────────────────────────────────────

async function getVideoDetail(videoId: string): Promise<TikTokPost[]> {
  const config = getConfig();

  // Support both full URL and video ID
  const id = videoId.match(/video\/(\d+)/)?.[1] || videoId;

  const result = await rapidApiGet(config, "api/video/detail", { videoId: id });
  if (result.error) throw new Error(result.error);

  const data = result.data as any;
  const video = data?.itemInfo?.itemStruct || data?.item || data?.data;
  if (!video) throw new Error(`Video not found: ${id}`);

  return [normalizeVideo(video)];
}

// ── Formatter ──────────────────────────────────────────────

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDuration(seconds: number): string {
  if (seconds <= 0) return "";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m${s}s` : `${s}s`;
}

function formatPosts(posts: TikTokPost[], sourceType: string, query: string): string {
  if (posts.length === 0) return `No TikTok results found (${sourceType}: ${query})`;

  const header = `## TikTok ${sourceType} results — ${posts.length} videos\n`;

  const lines = posts.map((p, i) => {
    const engagement = [
      `▶ ${formatNumber(p.plays)}`,
      `♥ ${formatNumber(p.likes)}`,
      `💬 ${formatNumber(p.comments)}`,
      `🔄 ${formatNumber(p.shares)}`,
      p.saves > 0 ? `🔖 ${formatNumber(p.saves)}` : "",
    ].filter(Boolean).join(" ");

    const score = p.plays * 0.001 + p.likes + p.comments * 3 + p.shares * 5 + p.saves * 2;
    const dur = formatDuration(p.duration);
    const desc = p.description.slice(0, 300).replace(/\n/g, " ");
    const tags = p.hashtags.slice(0, 8).join(" ");

    return [
      `### ${i + 1}. @${p.author} ${engagement} (score:${Math.round(score)})`,
      dur ? `> ${dur} | ${p.music || "original sound"}` : "",
      `> ${desc}${p.description.length > 300 ? "..." : ""}`,
      tags ? `> Tags: ${tags}` : "",
      `🔗 ${p.url}`,
      `📅 ${p.create_time}`,
    ].filter(Boolean).join("\n");
  });

  // JSON for piping
  const jsonData = posts.map((p) => ({
    text: p.description,
    author: p.author,
    url: p.url,
    timestamp: p.create_time,
    reactions: p.likes,
    comments: p.comments,
    shares: p.shares,
    views: p.plays,
    saves: p.saves,
    duration: p.duration,
    content_type: "video",
    hashtags: p.hashtags,
    music: p.music,
    source_type: sourceType,
    platform: "tiktok",
  }));

  return header + "\n" + lines.join("\n\n") + "\n\n---\n\n<json>\n" + JSON.stringify(jsonData, null, 2) + "\n</json>";
}

// ── Main execute ───────────────────────────────────────────

async function execute(params: Record<string, any>): Promise<string> {
  const sourceType = (params.source_type as string) || "search";
  const query = params.keyword as string;
  const count = (params.count as number) || 20;

  let posts: TikTokPost[];

  switch (sourceType) {
    case "search":
      posts = await searchVideos(query, count);
      break;
    case "user_posts":
      posts = await getUserPosts(query.replace(/^@/, ""), count);
      break;
    case "hashtag":
      posts = await getHashtagPosts(query, count);
      break;
    case "video_detail":
      posts = await getVideoDetail(query);
      break;
    default:
      return `Unknown source_type: ${sourceType}. Use: search, user_posts, hashtag, or video_detail`;
  }

  // Sort by engagement (skip for video_detail)
  if (sourceType !== "video_detail") {
    posts.sort((a, b) => {
      const scoreA = a.plays * 0.001 + a.likes + a.comments * 3 + a.shares * 5 + a.saves * 2;
      const scoreB = b.plays * 0.001 + b.likes + b.comments * 3 + b.shares * 5 + b.saves * 2;
      return scoreB - scoreA;
    });
  }

  return formatPosts(posts.slice(0, count), sourceType, query);
}

// ── Tool definition ────────────────────────────────────────

export const definition: ToolDefinition = {
  name: "tiktok_search",
  description: [
    "Search TikTok videos, user profiles, hashtags, or get video details.",
    "Modes: search (keyword), user_posts (user's videos), hashtag (hashtag feed), video_detail (single video).",
    "Returns full stats: plays, likes, comments, shares, saves, duration, music, hashtags.",
    "Output includes JSON for piping to content_scorer or content_analyzer.",
  ].join(" "),
  params: {
    keyword: z.string().describe("Search keyword, username (for user_posts), hashtag (for hashtag), or video URL/ID (for video_detail)"),
    source_type: z
      .enum(["search", "user_posts", "hashtag", "video_detail"])
      .default("search")
      .describe("Mode: search (keyword), user_posts (user's videos), hashtag (hashtag feed), video_detail (single video info)"),
    count: z.number().min(1).max(50).default(20).describe("Max results to return (1-50, ignored for video_detail)"),
  },
  envVars: ["RAPIDAPI_KEY"],
  execute,
};
