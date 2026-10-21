/**
 * youtube_channel — Browse YouTube channel videos + latest uploads.
 *
 * Provider priority:
 *   1. Supadata (SUPADATA_API_KEY) — reliable, supports channel metadata + video lists + per-video metadata
 *   2. TranscriptAPI (TRANSCRIPT_API_KEY) — channel/latest FREE, channel/videos = 1 credit
 *   3. RapidAPI YouTube search fallback (RAPIDAPI_KEY)
 */

import { z } from "zod";
import type { ToolDefinition } from "../../lib/tool-registry.js";
import {
  hasSupadataKey,
  supadataChannelInfo,
  supadataChannelVideos,
  supadataVideoMetaBatch,
} from "../../lib/supadata.js";

function formatNumber(n: number | string): string {
  const num = typeof n === "string" ? parseInt(n, 10) : n;
  if (isNaN(num)) return String(n);
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return String(num);
}

function formatDuration(seconds: number): string {
  if (!seconds) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

async function executeViaSupadata(
  channel: string,
  mode: string,
  limit: number,
  query?: string,
): Promise<string> {
  // Supadata doesn't support in-channel search server-side.
  // For `search` mode, fetch a larger list and filter titles client-side.
  const fetchLimit = mode === "search" ? Math.min(50, Math.max(limit * 5, 30)) : limit;

  const [info, videoIds] = await Promise.all([
    supadataChannelInfo(channel).catch(() => null),
    supadataChannelVideos(channel, fetchLimit),
  ]);

  if (!videoIds.length) throw new Error("Supadata returned no videos");

  const metas = await supadataVideoMetaBatch(videoIds, 5);

  let rows = metas;
  if (mode === "search" && query) {
    const q = query.toLowerCase();
    rows = metas.filter(
      (v) => v.title.toLowerCase().includes(q) || v.description.toLowerCase().includes(q),
    );
  }
  rows = rows.slice(0, limit);

  const header = info
    ? `## ${info.name} (@${info.handle?.replace(/^@/, "")}) — ${info.videoCount} videos, ${formatNumber(info.subscriberCount)} subs`
    : `## ${channel}`;

  const title =
    mode === "search" ? `${header}\nSearch: "${query}" (${rows.length} matches)\n` :
    mode === "all" ? `${header}\nAll videos (showing ${rows.length} of ${info?.videoCount ?? "?"})\n` :
    `${header}\nLatest ${rows.length} videos\n`;

  const lines: string[] = [title];
  rows.forEach((v, i) => {
    const date = v.uploadDate ? v.uploadDate.split("T")[0] : "";
    const views = v.viewCount ? `👁️${formatNumber(v.viewCount)}` : "";
    const dur = formatDuration(v.duration);
    const url = `https://youtube.com/watch?v=${v.id}`;
    lines.push(`**${i + 1}.** ${v.title}`);
    lines.push(`   📅 ${date} | ⏱️${dur} | ${views} | 🔗 ${url}`);
  });
  lines.push(`\n_Source: Supadata_`);
  return lines.join("\n");
}

async function execute(params: Record<string, any>): Promise<string> {
  const channel = params.channel as string;
  const mode = (params.mode as string) || "latest";
  const limit = (params.limit as number) || 15;
  const query = params.query as string | undefined;

  // Provider 1: Supadata
  if (hasSupadataKey()) {
    try {
      return await executeViaSupadata(channel, mode, limit, query);
    } catch (e: any) {
      // Fall through to other providers
    }
  }

  // Provider 2: TranscriptAPI
  if (process.env.TRANSCRIPT_API_KEY) {
    try {
      const { transcriptApiGet } = await import("../../lib/transcript-api.js");

      if (mode === "latest") {
        const data = await transcriptApiGet("/youtube/channel/latest", { channel });
        const videos = data.results || [];
        const channelInfo = data.channel || {};

        const sections: string[] = [];
        sections.push(`## ${channelInfo.title || channel} — Latest Videos\n`);

        videos.slice(0, limit).forEach((v: any, i: number) => {
          const views = v.viewCount ? `👁️${formatNumber(v.viewCount)}` : "";
          const published = v.published ? v.published.split("T")[0] : "";
          const url = `https://youtube.com/watch?v=${v.videoId}`;
          sections.push(`**${i + 1}.** ${views} ${v.title || "Untitled"}`);
          sections.push(`   📅 ${published} | 🔗 ${url}`);
        });

        return sections.join("\n");
      }

      if (mode === "search") {
        const data = await transcriptApiGet("/youtube/channel/search", { channel, q: query || "", limit: String(limit) });
        const videos = data.results || [];

        const sections: string[] = [];
        sections.push(`## ${channel} — Search: "${query}" (${videos.length} results)\n`);

        videos.slice(0, limit).forEach((v: any, i: number) => {
          const views = v.viewCountText || "";
          const url = `https://youtube.com/watch?v=${v.videoId}`;
          sections.push(`**${i + 1}.** ${v.title || "Untitled"} ${views}`);
          sections.push(`   📅 ${v.publishedTimeText || ""} | 🔗 ${url}`);
        });

        return sections.join("\n");
      }

      if (mode === "all") {
        const data = await transcriptApiGet("/youtube/channel/videos", { channel });
        const videos = data.results || [];
        const info = data.playlist_info || {};

        const sections: string[] = [];
        sections.push(`## ${info.ownerName || channel} — All Videos (${info.numVideos || "?"} total)\n`);

        videos.slice(0, limit).forEach((v: any, i: number) => {
          const views = v.viewCountText || "";
          const url = `https://youtube.com/watch?v=${v.videoId}`;
          sections.push(`**${i + 1}.** ${v.title || "Untitled"} ${views}`);
          sections.push(`   🔗 ${url}`);
        });

        if (data.has_more) {
          sections.push(`\n_Showing ${Math.min(videos.length, limit)} of ${info.numVideos || "many"}. Use mode="all" with pagination for more._`);
        }

        return sections.join("\n");
      }
    } catch (e: any) {
      // Fall through
    }
  }

  // Provider 3: Fallback to youtube_search with channel name
  try {
    const searchMod = await import("../youtube-search/index.ts");
    const result = await searchMod.definition.execute({ query: channel, maxResults: limit });
    return `## ${channel} (via search fallback)\n\n${result}`;
  } catch {
    return [
      "⚠️ Could not browse YouTube channel.",
      "",
      "**Option 1 (recommended):** Set SUPADATA_API_KEY — reliable channel + video metadata",
      "  Get key at: https://supadata.ai",
      "",
      "**Option 2:** Set TRANSCRIPT_API_KEY — channel/latest is FREE",
      "  Get key at: https://transcriptapi.com/signup",
      "",
      "**Option 3:** Set RAPIDAPI_KEY for YouTube search fallback",
    ].join("\n");
  }
}

export const definition: ToolDefinition = {
  name: "youtube_channel",
  description: [
    "Browse YouTube channel — latest videos, search within channel, or list all videos.",
    "Modes: latest (newest uploads), search (filter channel videos by keyword), all (paginated full list).",
    "Returns titles, upload dates, durations, view counts. Backed by Supadata / TranscriptAPI / RapidAPI.",
  ].join(" "),
  params: {
    channel: z.string().describe("YouTube channel (@handle, URL, or channel ID)"),
    mode: z.enum(["latest", "search", "all"]).default("latest").describe("latest, search (needs query), or all"),
    query: z.string().optional().describe("Search query within channel (for search mode)"),
    limit: z.number().min(1).max(100).default(15).describe("Max videos to return"),
  },
  execute,
};
