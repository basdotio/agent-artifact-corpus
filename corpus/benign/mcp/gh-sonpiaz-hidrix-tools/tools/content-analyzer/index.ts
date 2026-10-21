/**
 * content_analyzer — Analyze topics, patterns, intent, and trends from posts.
 *
 * Platform-aware analysis for TikTok, Instagram, Facebook, X, LinkedIn, Reddit, YouTube.
 * Detects content intent, format patterns, and platform-specific signals.
 *
 * Pure logic — no LLM, no external API.
 */

import { z } from "zod";
import type { ToolDefinition } from "../../lib/tool-registry.js";

// ── Topic keywords (improved: multi-word first to avoid partial matches) ──

const TOPIC_KEYWORDS: Record<string, { terms: string[]; weight: number }> = {
  ai_tools: {
    terms: ["machine learning", "artificial intelligence", "large language model", "chatgpt", "claude ai", "gemini ai",
      "cursor ide", "github copilot", "openai", "anthropic", "midjourney", "stable diffusion", "hugging face",
      "langchain", "llm", "gpt-4", "gpt-5", "ai agent", "ai tool", "ai app"],
    weight: 1.5,
  },
  business: {
    terms: ["startup", "marketing strategy", "sales funnel", "series a", "series b", "revenue growth",
      "business model", "entrepreneur", "investor", "pitch deck", "bootstrapped", "saas", "b2b", "b2c",
      "market fit", "product market", "go to market", "gtm strategy"],
    weight: 1.0,
  },
  vietnam_tech: {
    terms: ["vietnam tech", "việt nam", "công nghệ", "khởi nghiệp", "saigon", "hanoi", "hcmc",
      "fpt", "vng", "tiki", "shopee vietnam", "grab vietnam", "momo"],
    weight: 1.2,
  },
  learning: {
    terms: ["tutorial", "step by step", "how to", "learn to", "beginner guide", "advanced guide",
      "free course", "workshop", "training", "lesson", "cheat sheet", "crash course"],
    weight: 1.0,
  },
  community: {
    terms: ["meetup", "tech event", "hackathon", "conference", "networking event", "community",
      "collaboration", "open source", "contributor"],
    weight: 0.8,
  },
  tools_products: {
    terms: ["new tool", "just launched", "product hunt", "app launch", "chrome extension", "vscode extension",
      "saas tool", "free tool", "open source tool", "api", "sdk", "framework"],
    weight: 1.0,
  },
  career: {
    terms: ["job opening", "we're hiring", "remote job", "career", "resume tips", "interview tips",
      "salary", "freelance", "side hustle", "quit my job", "got hired", "tech salary"],
    weight: 0.9,
  },
  crypto_web3: {
    terms: ["cryptocurrency", "bitcoin", "ethereum", "blockchain", "web3", "nft", "defi", "token",
      "solana", "crypto market", "bull run", "bear market"],
    weight: 0.8,
  },
  content_creation: {
    terms: ["content strategy", "content creation", "viral video", "youtube shorts", "tiktok trend",
      "reels", "newsletter", "podcast", "blogging", "creator economy", "monetize", "brand deal"],
    weight: 1.0,
  },
  design: {
    terms: ["ui design", "ux design", "figma", "web design", "branding", "logo design", "creative",
      "design system", "prototype", "wireframe", "visual design"],
    weight: 0.8,
  },
  ecommerce: {
    terms: ["dropshipping", "ecommerce", "shopify", "amazon fba", "online store", "print on demand",
      "affiliate marketing", "product listing", "conversion rate"],
    weight: 1.0,
  },
  personal_brand: {
    terms: ["personal brand", "build audience", "grow followers", "engagement rate", "content calendar",
      "hook", "cta", "call to action", "storytelling", "thought leader"],
    weight: 1.1,
  },
};

// ── Content intent detection ───────────────────────────────

type ContentIntent =
  | "educational"      // teaching, tutorial, how-to
  | "promotional"      // selling, launching, advertising
  | "engagement_bait"  // questions, polls, controversial takes
  | "storytelling"     // personal story, journey, case study
  | "news"             // breaking news, announcements
  | "entertainment"    // humor, memes, trends
  | "inspirational"    // motivational, success story
  | "opinion"          // hot takes, reviews, comparisons
  | "curated"          // list, roundup, recommendation
  | "unknown";

const INTENT_PATTERNS: Array<{ intent: ContentIntent; patterns: RegExp[]; textSignals: string[] }> = [
  {
    intent: "educational",
    patterns: [
      /(?:how to|step[\s-]by[\s-]step|tutorial|guide|learn|tip[s]?\b|trick[s]?\b|lesson|here'?s how)/i,
      /(?:\d+\s+(?:ways?|steps?|tips?|things?|mistakes?|secrets?)\s+(?:to|for|about))/i,
      /(?:thread|🧵)/i,
    ],
    textSignals: ["explained", "breakdown", "deep dive", "cheat sheet", "masterclass"],
  },
  {
    intent: "promotional",
    patterns: [
      /(?:just launched|now available|check out|sign up|try it|link in bio|use code|discount|limited time)/i,
      /(?:we'?re? (?:building|launching|releasing)|introducing|announcing|pre-order)/i,
    ],
    textSignals: ["product hunt", "beta access", "early access", "free trial", "waitlist"],
  },
  {
    intent: "engagement_bait",
    patterns: [
      /(?:agree\s*\?|thoughts\s*\?|what do you think|am i wrong|hot take|unpopular opinion|controversial)/i,
      /(?:like if|comment if|share if|tag someone|who else|raise your hand)/i,
      /(?:which one|would you rather|this or that)/i,
    ],
    textSignals: ["debate", "poll", "vote", "drop a", "let me know"],
  },
  {
    intent: "storytelling",
    patterns: [
      /(?:my journey|my story|how i|i quit|i built|i went from|i made|here'?s what happened)/i,
      /(?:a year ago|months? ago.*(?:now|today)|before and after|transformation)/i,
    ],
    textSignals: ["failed", "succeeded", "changed my life", "turning point", "pivoted"],
  },
  {
    intent: "news",
    patterns: [
      /(?:breaking|just in|announced|confirmed|officially|report[s]?:|according to|sources say)/i,
      /(?:update:|news:|alert:)/i,
    ],
    textSignals: ["acquisition", "funding round", "shut down", "ipo", "layoffs"],
  },
  {
    intent: "entertainment",
    patterns: [
      /(?:lol|lmao|😂|🤣|💀|😭|bruh|no way|i can'?t|dead|relatable|mood)/i,
      /(?:meme|trend|challenge|duet|stitch|pov:)/i,
    ],
    textSignals: ["comedy", "skit", "parody", "roast"],
  },
  {
    intent: "inspirational",
    patterns: [
      /(?:never give up|keep going|you can do|believe in|don'?t quit|hard work|grind|hustle|mindset)/i,
      /(?:success|motivation|discipline|consistency|growth mindset)/i,
    ],
    textSignals: ["proof that", "it's possible", "dream big", "manifest"],
  },
  {
    intent: "opinion",
    patterns: [
      /(?:i think|my take|here'?s why|the truth about|overrated|underrated|stop using|unpopular)/i,
      /(?:review|comparison|vs\b|versus|better than|worse than)/i,
    ],
    textSignals: ["honest review", "brutally honest", "real talk", "hot take"],
  },
  {
    intent: "curated",
    patterns: [
      /(?:top \d+|best \d+|\d+ (?:best|top|must)|roundup|collection|list of|favorites)/i,
      /(?:bookmark this|save this|resources|tools i use)/i,
    ],
    textSignals: ["compilation", "starter pack", "toolkit", "stack"],
  },
];

function detectIntent(text: string): { primary: ContentIntent; confidence: number; secondary?: ContentIntent } {
  const lower = text.toLowerCase();
  const scores: Record<ContentIntent, number> = {} as any;

  for (const { intent, patterns, textSignals } of INTENT_PATTERNS) {
    let score = 0;
    for (const p of patterns) {
      if (p.test(text)) score += 2;
    }
    for (const signal of textSignals) {
      if (lower.includes(signal)) score += 1;
    }
    if (score > 0) scores[intent] = score;
  }

  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  if (sorted.length === 0) return { primary: "unknown", confidence: 0 };

  const maxScore = sorted[0][1];
  const confidence = Math.min(1, maxScore / 6); // 6 = max reasonable score

  return {
    primary: sorted[0][0] as ContentIntent,
    confidence: Math.round(confidence * 100) / 100,
    secondary: sorted.length > 1 ? sorted[1][0] as ContentIntent : undefined,
  };
}

// ── Platform-specific format detection ─────────────────────

interface PlatformProfile {
  name: string;
  contentTypes: Record<string, number>;
  avgDuration?: number;
  hashtagDensity: number;
  avgCaptionLength: number;
  topHashtags: Array<{ tag: string; count: number; avgEngagement: number }>;
  engagementByType: Record<string, { count: number; avgEngagement: number }>;
  viralThreshold: number;
  bestPerformingFormat: string;
}

function detectPlatform(posts: any[]): string {
  if (posts.length === 0) return "unknown";
  // Check explicit platform field first
  const explicit = posts[0]?.platform;
  if (explicit) return explicit;

  // Infer from data shape
  const sample = posts[0];
  if (sample.views !== undefined && sample.saves !== undefined && sample.duration !== undefined) return "tiktok";
  if (sample.content_type && ["image", "video", "carousel", "reel"].includes(sample.content_type)) return "instagram";
  if (sample.source_type && ["group", "page", "search", "ad"].includes(sample.source_type)) return "facebook";
  if (sample.retweets !== undefined || sample.quotes !== undefined) return "x";
  if (sample.reposts !== undefined) return "linkedin";
  if (sample.subreddit !== undefined) return "reddit";
  return "unknown";
}

function buildPlatformProfile(posts: any[], platform: string): PlatformProfile {
  const contentTypes: Record<string, number> = {};
  let totalDuration = 0;
  let durationCount = 0;
  let totalCaptionLength = 0;
  const allHashtags: Record<string, { count: number; totalEngagement: number }> = {};
  const engagementByType: Record<string, { count: number; totalEngagement: number }> = {};
  const engagements: number[] = [];

  for (const post of posts) {
    const text = post.text || "";
    totalCaptionLength += text.length;

    // Content type
    const ctype = post.content_type || (post.views > 0 ? "video" : "text");
    contentTypes[ctype] = (contentTypes[ctype] || 0) + 1;

    // Duration
    if (post.duration > 0) {
      totalDuration += post.duration;
      durationCount++;
    }

    // Hashtags
    const tags: string[] = post.hashtags || (text.match(/#[\w\u00C0-\u024F]+/g) || []);
    const eng = computeEngagement(post, platform);
    engagements.push(eng);

    for (const tag of tags) {
      const t = tag.toLowerCase();
      if (!allHashtags[t]) allHashtags[t] = { count: 0, totalEngagement: 0 };
      allHashtags[t].count++;
      allHashtags[t].totalEngagement += eng;
    }

    // Engagement by type
    if (!engagementByType[ctype]) engagementByType[ctype] = { count: 0, totalEngagement: 0 };
    engagementByType[ctype].count++;
    engagementByType[ctype].totalEngagement += eng;
  }

  // Top hashtags
  const topHashtags = Object.entries(allHashtags)
    .map(([tag, data]) => ({ tag, count: data.count, avgEngagement: Math.round(data.totalEngagement / data.count) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);

  // Hashtag density
  const totalTags = Object.values(allHashtags).reduce((sum, d) => sum + d.count, 0);
  const hashtagDensity = Math.round((totalTags / Math.max(posts.length, 1)) * 10) / 10;

  // Engagement by type (averaged)
  const engByType: Record<string, { count: number; avgEngagement: number }> = {};
  for (const [type, data] of Object.entries(engagementByType)) {
    engByType[type] = { count: data.count, avgEngagement: Math.round(data.totalEngagement / data.count) };
  }

  // Best performing format
  const bestFormat = Object.entries(engByType)
    .sort((a, b) => b[1].avgEngagement - a[1].avgEngagement)[0]?.[0] || "unknown";

  // Viral threshold (p90 engagement)
  engagements.sort((a, b) => a - b);
  const p90Index = Math.floor(engagements.length * 0.9);
  const viralThreshold = engagements[p90Index] || 0;

  return {
    name: platform,
    contentTypes,
    avgDuration: durationCount > 0 ? Math.round(totalDuration / durationCount) : undefined,
    hashtagDensity,
    avgCaptionLength: Math.round(totalCaptionLength / Math.max(posts.length, 1)),
    topHashtags,
    engagementByType: engByType,
    viralThreshold,
    bestPerformingFormat: bestFormat,
  };
}

// ── Platform-specific engagement formula ───────────────────

function computeEngagement(post: any, platform: string): number {
  const reactions = Number(post.reactions) || Number(post.likes) || 0;
  const comments = Number(post.comments) || 0;
  const shares = Number(post.shares) || Number(post.retweets) || Number(post.reposts) || 0;
  const views = Number(post.views) || Number(post.plays) || 0;
  const saves = Number(post.saves) || Number(post.bookmarks) || 0;

  switch (platform) {
    case "tiktok":
      // TikTok: views are cheap, saves/shares are high-intent signals
      return views * 0.001 + reactions + comments * 3 + shares * 5 + saves * 4;
    case "instagram":
      // Instagram: saves are the strongest signal, views for reels
      return reactions + comments * 3 + saves * 5 + views * 0.005;
    case "facebook":
      // Facebook: shares are king (organic reach), comments drive algorithm
      return reactions + comments * 3 + shares * 7;
    case "x":
      // X: retweets/quotes amplify, bookmarks = save-for-later intent
      return reactions + comments * 2 + shares * 4 + saves * 3;
    case "linkedin":
      // LinkedIn: comments are the #1 signal, reposts secondary
      return reactions + comments * 5 + shares * 3;
    default:
      return reactions + comments * 3 + shares * 5;
  }
}

// ── Analysis functions ─────────────────────────────────────

function analyzeTopics(posts: any[], platform: string): Record<string, { count: number; avgEngagement: number; topPost: string }> {
  const topics: Record<string, { count: number; totalEngagement: number; topScore: number; topPost: string }> = {};

  for (const post of posts) {
    const text = ((post.text || "") + " " + (post.author || "")).toLowerCase();
    const engagement = computeEngagement(post, platform);

    for (const [topic, config] of Object.entries(TOPIC_KEYWORDS)) {
      // Use word boundary-aware matching for short terms
      const matched = config.terms.some((term) => {
        if (term.length <= 3) {
          // Short terms: require word boundary
          return new RegExp(`\\b${term}\\b`, "i").test(text);
        }
        return text.includes(term);
      });

      if (matched) {
        if (!topics[topic]) topics[topic] = { count: 0, totalEngagement: 0, topScore: 0, topPost: "" };
        topics[topic].count++;
        topics[topic].totalEngagement += engagement * config.weight;
        if (engagement > topics[topic].topScore) {
          topics[topic].topScore = engagement;
          topics[topic].topPost = (post.text || "").slice(0, 100);
        }
      }
    }
  }

  const result: Record<string, { count: number; avgEngagement: number; topPost: string }> = {};
  for (const [topic, data] of Object.entries(topics)) {
    result[topic] = {
      count: data.count,
      avgEngagement: Math.round(data.totalEngagement / data.count),
      topPost: data.topPost,
    };
  }
  return result;
}

function analyzePatterns(posts: any[], platform: string): Record<string, any> {
  let totalLength = 0;
  let withMedia = 0;
  let withLinks = 0;
  let questionPosts = 0;
  let listPosts = 0;
  let emojiHeavy = 0;
  let mentionPosts = 0;
  let ctaPosts = 0;
  let hookPosts = 0;
  const lengths: number[] = [];

  for (const post of posts) {
    const text = post.text || "";
    totalLength += text.length;
    lengths.push(text.length);

    if (/https?:\/\//.test(text)) withLinks++;
    if (/\.(jpg|png|gif|mp4|video)/i.test(text) || post.image || post.video || post.media_url || post.content_type === "image" || post.content_type === "carousel") withMedia++;
    if (text.includes("?")) questionPosts++;
    if (/^\d+[\.\)]/m.test(text) || /^[-•]/m.test(text)) listPosts++;
    if ((text.match(/[\u{1F000}-\u{1FFFF}]/gu) || []).length >= 3) emojiHeavy++;
    if (/@\w+/.test(text)) mentionPosts++;
    if (/(?:link in bio|comment below|share this|follow|subscribe|sign up|click|tap|swipe)/i.test(text)) ctaPosts++;
    // Hook detection: first line is short + attention-grabbing
    const firstLine = text.split(/\n/)[0] || "";
    if (firstLine.length < 80 && (/[!?🔥💡⚡🚀]/.test(firstLine) || /^(?:stop|wait|imagine|here'?s|the truth|nobody)/i.test(firstLine))) hookPosts++;
  }

  const n = Math.max(posts.length, 1);
  lengths.sort((a, b) => a - b);

  const base: Record<string, any> = {
    total_posts: posts.length,
    avg_length: Math.round(totalLength / n),
    median_length: lengths[Math.floor(lengths.length / 2)] || 0,
    with_media: `${Math.round((withMedia / n) * 100)}%`,
    with_links: `${Math.round((withLinks / n) * 100)}%`,
    question_posts: `${Math.round((questionPosts / n) * 100)}%`,
    list_format: `${Math.round((listPosts / n) * 100)}%`,
    emoji_heavy: `${Math.round((emojiHeavy / n) * 100)}%`,
    with_mentions: `${Math.round((mentionPosts / n) * 100)}%`,
    has_cta: `${Math.round((ctaPosts / n) * 100)}%`,
    has_hook: `${Math.round((hookPosts / n) * 100)}%`,
  };

  // Platform-specific patterns
  if (platform === "tiktok") {
    const durations = posts.filter((p) => p.duration > 0).map((p) => p.duration);
    if (durations.length > 0) {
      durations.sort((a, b) => a - b);
      base.avg_duration = `${Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)}s`;
      base.median_duration = `${durations[Math.floor(durations.length / 2)]}s`;
      base.short_form = `${Math.round((durations.filter((d) => d <= 30).length / durations.length) * 100)}% (≤30s)`;
      base.mid_form = `${Math.round((durations.filter((d) => d > 30 && d <= 60).length / durations.length) * 100)}% (30-60s)`;
      base.long_form = `${Math.round((durations.filter((d) => d > 60).length / durations.length) * 100)}% (>60s)`;
    }
    const withMusic = posts.filter((p) => p.music && !p.music.includes("original")).length;
    base.trending_sound = `${Math.round((withMusic / n) * 100)}%`;
    base.original_sound = `${Math.round(((n - withMusic) / n) * 100)}%`;
  }

  if (platform === "instagram") {
    const types = posts.reduce((acc: Record<string, number>, p) => {
      const t = p.content_type || "image";
      acc[t] = (acc[t] || 0) + 1;
      return acc;
    }, {});
    base.content_mix = Object.entries(types)
      .map(([t, c]) => `${t}: ${Math.round(((c as number) / n) * 100)}%`)
      .join(", ");
  }

  return base;
}

function analyzeIntent(posts: any[]): Record<string, any> {
  const intentCounts: Record<ContentIntent, { count: number; totalEngagement: number; examples: string[] }> = {} as any;

  for (const post of posts) {
    const text = post.text || "";
    const { primary } = detectIntent(text);
    if (!intentCounts[primary]) intentCounts[primary] = { count: 0, totalEngagement: 0, examples: [] };
    intentCounts[primary].count++;
    intentCounts[primary].totalEngagement += (Number(post.reactions) || 0) + (Number(post.comments) || 0) * 3;
    if (intentCounts[primary].examples.length < 2) {
      intentCounts[primary].examples.push(text.slice(0, 80));
    }
  }

  const sorted = Object.entries(intentCounts)
    .sort((a, b) => b[1].count - a[1].count)
    .map(([intent, data]) => ({
      intent,
      count: data.count,
      percentage: `${Math.round((data.count / Math.max(posts.length, 1)) * 100)}%`,
      avgEngagement: Math.round(data.totalEngagement / Math.max(data.count, 1)),
      examples: data.examples,
    }));

  return { distribution: sorted };
}

function analyzeTimingHeatmap(posts: any[]): Record<string, number> {
  const hourCounts: Record<string, number> = {};
  const dayCounts: Record<string, number> = {};

  for (const post of posts) {
    if (!post.timestamp) continue;
    const date = new Date(post.timestamp);
    if (isNaN(date.getTime())) continue;

    const hour = date.getUTCHours();
    const day = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][date.getUTCDay()];

    const hourKey = `${hour}:00 UTC`;
    hourCounts[hourKey] = (hourCounts[hourKey] || 0) + 1;
    dayCounts[day] = (dayCounts[day] || 0) + 1;
  }

  return { ...dayCounts, ...hourCounts };
}

function analyzeAuthors(posts: any[], platform: string): Array<{ author: string; posts: number; totalEngagement: number; avgEngagement: number }> {
  const authors: Record<string, { posts: number; totalEngagement: number }> = {};

  for (const post of posts) {
    const author = post.author || "unknown";
    if (!authors[author]) authors[author] = { posts: 0, totalEngagement: 0 };
    authors[author].posts++;
    authors[author].totalEngagement += computeEngagement(post, platform);
  }

  return Object.entries(authors)
    .map(([author, data]) => ({
      author,
      posts: data.posts,
      totalEngagement: data.totalEngagement,
      avgEngagement: Math.round(data.totalEngagement / data.posts),
    }))
    .sort((a, b) => b.totalEngagement - a.totalEngagement)
    .slice(0, 20);
}

// ── Main execute ───────────────────────────────────────────

async function execute(params: Record<string, any>): Promise<string> {
  const postsJson = params.posts_json as string;
  const analysisType = params.analysis_type as string;

  let posts: any[];
  try {
    posts = JSON.parse(postsJson);
    if (!Array.isArray(posts)) throw new Error("not array");
  } catch {
    return "Error: posts_json must be a valid JSON array of post objects";
  }

  if (posts.length === 0) return "No posts to analyze.";

  const platform = detectPlatform(posts);
  const sections: string[] = [`## Content Analysis — ${posts.length} posts (${platform})\n`];

  // Platform profile
  if (analysisType === "full") {
    const profile = buildPlatformProfile(posts, platform);
    sections.push("### 📱 Platform Profile\n");
    sections.push(`- **Platform**: ${profile.name}`);
    sections.push(`- **Content types**: ${Object.entries(profile.contentTypes).map(([t, c]) => `${t}(${c})`).join(", ")}`);
    if (profile.avgDuration) sections.push(`- **Avg video duration**: ${profile.avgDuration}s`);
    sections.push(`- **Hashtag density**: ${profile.hashtagDensity} tags/post`);
    sections.push(`- **Avg caption length**: ${profile.avgCaptionLength} chars`);
    sections.push(`- **Best performing format**: ${profile.bestPerformingFormat}`);
    sections.push(`- **Viral threshold (p90)**: ${profile.viralThreshold} engagement`);
    if (profile.topHashtags.length > 0) {
      sections.push(`\n**Top hashtags:**`);
      for (const h of profile.topHashtags.slice(0, 10)) {
        sections.push(`- ${h.tag} (${h.count}x, avg eng: ${h.avgEngagement})`);
      }
    }
    sections.push("");
  }

  // Intent analysis
  if (analysisType === "full" || analysisType === "intent") {
    const intentData = analyzeIntent(posts);
    sections.push("### 🎯 Content Intent\n");
    sections.push("| Intent | Count | % | Avg Engagement | Example |");
    sections.push("|---|---|---|---|---|");
    for (const item of intentData.distribution) {
      const example = item.examples[0]?.replace(/\|/g, "\\|") || "";
      sections.push(`| ${item.intent} | ${item.count} | ${item.percentage} | ${item.avgEngagement} | ${example}... |`);
    }
    sections.push("");
  }

  // Topics
  if (analysisType === "full" || analysisType === "topics") {
    const topics = analyzeTopics(posts, platform);
    const sorted = Object.entries(topics).sort((a, b) => b[1].count - a[1].count);
    sections.push("### 📊 Topic Clusters\n");
    sections.push("| Topic | Posts | Avg Engagement | Top Post |");
    sections.push("|---|---|---|---|");
    for (const [topic, data] of sorted) {
      sections.push(`| ${topic} | ${data.count} | ${data.avgEngagement} | ${data.topPost.replace(/\|/g, "\\|")}... |`);
    }
    sections.push("");
  }

  // Patterns (platform-aware)
  if (analysisType === "full" || analysisType === "patterns") {
    const patterns = analyzePatterns(posts, platform);
    sections.push("### 🔍 Content Patterns\n");
    for (const [key, value] of Object.entries(patterns)) {
      sections.push(`- **${key.replace(/_/g, " ")}**: ${value}`);
    }
    sections.push("");
  }

  // Timing
  if (analysisType === "full" || analysisType === "trends") {
    const timing = analyzeTimingHeatmap(posts);
    sections.push("### ⏰ Posting Time Heatmap\n");
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    for (const day of days) {
      if (timing[day]) sections.push(`- **${day}**: ${timing[day]} posts`);
    }
    sections.push("");

    const hours = Object.entries(timing)
      .filter(([k]) => k.includes("UTC"))
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    if (hours.length > 0) {
      sections.push("**Peak hours (UTC):**");
      for (const [hour, count] of hours) {
        sections.push(`- ${hour}: ${count} posts`);
      }
      sections.push("");
    }
  }

  // Authors
  if (analysisType === "full" || analysisType === "trends") {
    const authors = analyzeAuthors(posts, platform);
    sections.push("### 👥 Top Authors\n");
    sections.push("| Author | Posts | Total Engagement | Avg Engagement |");
    sections.push("|---|---|---|---|");
    for (const a of authors.slice(0, 10)) {
      sections.push(`| ${a.author} | ${a.posts} | ${a.totalEngagement} | ${a.avgEngagement} |`);
    }
    sections.push("");
  }

  return sections.join("\n");
}

export const definition: ToolDefinition = {
  name: "content_analyzer",
  description: [
    "Analyze posts for content intent, topic clusters, platform-specific patterns, posting trends, and author leaderboard.",
    "Platform-aware: auto-detects TikTok/Instagram/Facebook/X/LinkedIn and applies platform-specific engagement formulas.",
    "Detects content intent: educational, promotional, engagement_bait, storytelling, news, entertainment, inspirational, opinion, curated.",
    "Input: JSON array of posts (from any scraper tool). No external API needed.",
  ].join(" "),
  params: {
    posts_json: z.string().describe("JSON array of post objects with fields: text, author, url, timestamp, reactions/likes, comments, shares, views, saves, content_type, hashtags, platform"),
    analysis_type: z
      .enum(["full", "topics", "patterns", "trends", "intent"])
      .default("full")
      .describe("Type of analysis: full (all), topics, patterns, trends, or intent (content intent detection)"),
  },
  execute,
};
