/**
 * Supadata API client — YouTube channel metadata, video lists, video metadata, transcripts.
 *
 * Docs: https://supadata.ai
 * Auth: x-api-key header
 *
 * Endpoints used:
 *   GET /v1/youtube/channel?id=<handle|UCxxx>          — channel info
 *   GET /v1/youtube/channel/videos?id=<...>&limit=N    — recent video IDs (max 50/call)
 *   GET /v1/youtube/video?id=<videoId>                  — full metadata incl. title, uploadDate, duration, description
 */

const BASE_URL = "https://api.supadata.ai/v1";

export function hasSupadataKey(): boolean {
  return !!process.env.SUPADATA_API_KEY;
}

export function requireSupadataKey(): string {
  const key = process.env.SUPADATA_API_KEY;
  if (!key) throw new Error("Missing SUPADATA_API_KEY. Get one at https://supadata.ai");
  return key;
}

async function supadataGet(path: string, params: Record<string, string>): Promise<any> {
  const key = requireSupadataKey();
  const url = new URL(`${BASE_URL}${path}`);
  for (const [k, v] of Object.entries(params)) {
    if (v) url.searchParams.set(k, v);
  }

  const res = await fetch(url.toString(), {
    headers: { "x-api-key": key },
    signal: AbortSignal.timeout(30_000),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supadata error (${res.status}): ${body.slice(0, 300)}`);
  }

  return res.json();
}

export interface SupadataChannel {
  id: string;
  name: string;
  handle: string;
  description: string;
  subscriberCount: number;
  videoCount: number;
  viewCount: number;
}

export interface SupadataVideo {
  id: string;
  title: string;
  description: string;
  uploadDate: string;
  viewCount: number;
  likeCount: number;
  duration: number;
  channel: { id: string; name: string };
}

/** Normalize channel input to a form Supadata accepts (channelId or @handle). */
export function normalizeChannelInput(input: string): string {
  const s = input.trim();
  const urlMatch = s.match(/youtube\.com\/(@[\w.-]+|channel\/(UC[\w-]+))/);
  if (urlMatch) return urlMatch[1].startsWith("@") ? urlMatch[1] : urlMatch[2];
  if (s.startsWith("UC") && s.length > 20) return s;
  if (s.startsWith("@")) return s;
  return `@${s}`;
}

export async function supadataChannelInfo(channel: string): Promise<SupadataChannel> {
  const id = normalizeChannelInput(channel);
  return supadataGet("/youtube/channel", { id });
}

export async function supadataChannelVideos(channel: string, limit = 30): Promise<string[]> {
  const id = normalizeChannelInput(channel);
  const data = await supadataGet("/youtube/channel/videos", { id, limit: String(Math.min(limit, 50)) });
  return data.videoIds || [];
}

export async function supadataVideoMeta(videoId: string): Promise<SupadataVideo> {
  return supadataGet("/youtube/video", { id: videoId });
}

/** Fetch metadata for many videos in parallel with a concurrency cap. */
export async function supadataVideoMetaBatch(videoIds: string[], concurrency = 5): Promise<SupadataVideo[]> {
  const results: SupadataVideo[] = [];
  for (let i = 0; i < videoIds.length; i += concurrency) {
    const batch = videoIds.slice(i, i + concurrency);
    const metas = await Promise.all(
      batch.map((id) => supadataVideoMeta(id).catch((e) => ({ id, title: `[error: ${e.message}]`, description: "", uploadDate: "", viewCount: 0, likeCount: 0, duration: 0, channel: { id: "", name: "" } } as SupadataVideo)))
    );
    results.push(...metas);
  }
  return results;
}
