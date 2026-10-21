import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Repo root: mcp/lib -> mcp -> repo */
export const REPO_ROOT = resolve(__dirname, "../..");
export const DAYS_ROOT = join(REPO_ROOT, "days");
export const SKILL_PATH = join(
  __dirname,
  "../skills/masterfabric-academy/SKILL.md",
);

export type TrackId =
  | "go"
  | "flutter"
  | "expo"
  | "devops"
  | "nestjs"
  | "nextjs"
  | "typescript"
  | "graphql"
  | "ai-agents"
  | "oop"
  | "sdlc"
  | "git";

export interface TrackMeta {
  id: TrackId;
  name: string;
  days: number;
  folder: string;
  roadmapFile: string;
  focus: string;
  profile: string;
}

export const TRACKS: Record<TrackId, TrackMeta> = {
  go: {
    id: "go",
    name: "Go",
    days: 100,
    folder: "go",
    roadmapFile: "go_roadmap.md",
    focus: "Idiomatic Go — concurrency, HTTP/REST, data, auth, clean arch, gRPC, observability, CI/CD",
    profile: "Backend engineer shipping high-traffic, secure services",
  },
  flutter: {
    id: "flutter",
    name: "Flutter",
    days: 100,
    folder: "flutter",
    roadmapFile: "flutter_roadmap.md",
    focus: "Dart → Flutter UI → state → APIs → testing → platform channels → CI/CD",
    profile: "Mobile engineer building production-quality cross-platform apps",
  },
  expo: {
    id: "expo",
    name: "Expo / React Native",
    days: 100,
    folder: "expo",
    roadmapFile: "expo_roadmap.md",
    focus: "JS/TS → React/Expo → navigation → state → testing → EAS",
    profile: "Mobile engineer delivering Expo apps with solid DX and release hygiene",
  },
  devops: {
    id: "devops",
    name: "DevOps",
    days: 100,
    folder: "devops",
    roadmapFile: "devops_roadmap.md",
    focus: "Linux → Git → Docker → CI/CD → cloud → IaC → K8s → monitoring → security",
    profile: "Platform engineer enabling safe, high-throughput delivery",
  },
  nestjs: {
    id: "nestjs",
    name: "NestJS",
    days: 100,
    folder: "nestjs",
    roadmapFile: "nestjs_roadmap.md",
    focus: "Nest basics → DB/auth → testing → microservices → DDD/CQRS → enterprise patterns",
    profile: "Node backend engineer for scalable, secure APIs",
  },
  nextjs: {
    id: "nextjs",
    name: "Next.js",
    days: 100,
    folder: "nextjs",
    roadmapFile: "nextjs_roadmap.md",
    focus: "React/Next → full-stack → App Router → performance → testing → SaaS delivery",
    profile: "Full-stack engineer for performant, secure web products",
  },
  typescript: {
    id: "typescript",
    name: "TypeScript",
    days: 100,
    folder: "typescript",
    roadmapFile: "typescript_roadmap.md",
    focus: "Types → generics → advanced types → Zod → testing → library/monorepo contracts",
    profile: "Type-safe engineer designing durable APIs and libraries",
  },
  graphql: {
    id: "graphql",
    name: "GraphQL",
    days: 100,
    folder: "graphql",
    roadmapFile: "graphql_roadmap.md",
    focus: "SDL → resolvers → auth → clients → subscriptions → DataLoader → federation",
    profile: "API engineer for schema-first, secure GraphQL platforms",
  },
  "ai-agents": {
    id: "ai-agents",
    name: "AI Agents",
    days: 100,
    folder: "ai-agents",
    roadmapFile: "ai-agents_roadmap.md",
    focus: "Agent fundamentals → tools/memory/RAG → multi-agent → production domain agents",
    profile: "AI engineer shipping reliable, tool-using agents",
  },
  oop: {
    id: "oop",
    name: "OOP",
    days: 20,
    folder: "oop",
    roadmapFile: "oop_roadmap.md",
    focus: "Classes, encapsulation, inheritance, polymorphism, SOLID, patterns",
    profile: "Foundational design thinking for maintainable systems",
  },
  sdlc: {
    id: "sdlc",
    name: "SDLC",
    days: 16,
    folder: "sdlc",
    roadmapFile: "sdlc_roadmap.md",
    focus: "Requirements → design → build → quality → release → operate/improve",
    profile: "Delivery-minded engineer who owns the full software lifecycle",
  },
  git: {
    id: "git",
    name: "Git",
    days: 16,
    folder: "git",
    roadmapFile: "git_roadmap.md",
    focus: "Init → branch → merge → remotes → undo → rebase → cherry-pick → stash → tags",
    profile: "Collaborative engineer with safe version-control habits",
  },
};

export function listTracks(): TrackMeta[] {
  return Object.values(TRACKS);
}

export function getTrack(trackId: string): TrackMeta {
  const track = TRACKS[trackId as TrackId];
  if (!track) {
    const known = Object.keys(TRACKS).join(", ");
    throw new Error(`Unknown track "${trackId}". Known tracks: ${known}`);
  }
  return track;
}

export function trackDir(track: TrackMeta): string {
  return join(DAYS_ROOT, track.folder);
}

export function readRoadmap(trackId: string): string {
  const track = getTrack(trackId);
  const path = join(trackDir(track), track.roadmapFile);
  if (!existsSync(path)) {
    throw new Error(`Roadmap not found: ${path}`);
  }
  return readFileSync(path, "utf8");
}

export function readDay(trackId: string, day: number): string {
  const track = getTrack(trackId);
  if (!Number.isInteger(day) || day < 1 || day > track.days) {
    throw new Error(
      `Day must be an integer between 1 and ${track.days} for track "${track.id}"`,
    );
  }
  const path = join(trackDir(track), `${day}.md`);
  if (!existsSync(path)) {
    throw new Error(`Day file not found: ${path}`);
  }
  return readFileSync(path, "utf8");
}

export function listAvailableDays(trackId: string): number[] {
  const track = getTrack(trackId);
  const dir = trackDir(track);
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .map((name) => {
      const match = /^(\d+)\.md$/.exec(name);
      return match ? Number(match[1]) : null;
    })
    .filter((n): n is number => n !== null)
    .sort((a, b) => a - b);
}

export interface PhaseBlock {
  range: string;
  start: number;
  end: number;
  focusArea: string;
  content: string;
  goal: string;
}

/** Parse 5-day (or similar) roadmap table rows into phase blocks. */
export function parsePhases(roadmapMarkdown: string): PhaseBlock[] {
  const phases: PhaseBlock[] = [];
  const rowRe =
    /^\|\s*\*\*([^*]+)\*\*\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$/gm;

  for (const match of roadmapMarkdown.matchAll(rowRe)) {
    const range = match[1].trim();
    const focusArea = match[2].trim();
    const content = match[3].replace(/\*\*/g, "").trim();
    const goal = match[4].replace(/\*\*/g, "").trim();
    const nums = range.match(/\d+/g)?.map(Number) ?? [];
    if (nums.length === 0) continue;
    const start = nums[0];
    const end = nums.length > 1 ? nums[1] : nums[0];
    phases.push({ range, start, end, focusArea, content, goal });
  }
  return phases;
}

export function phaseForDay(trackId: string, day: number): PhaseBlock | null {
  const phases = parsePhases(readRoadmap(trackId));
  return phases.find((p) => day >= p.start && day <= p.end) ?? null;
}

export function readSkill(): string {
  if (!existsSync(SKILL_PATH)) {
    throw new Error(`Academy skill not found: ${SKILL_PATH}`);
  }
  return readFileSync(SKILL_PATH, "utf8");
}

export function dayTitle(markdown: string): string {
  const line = markdown.split("\n").find((l) => l.startsWith("# "));
  return line ? line.replace(/^#\s+/, "").trim() : "Untitled day";
}
