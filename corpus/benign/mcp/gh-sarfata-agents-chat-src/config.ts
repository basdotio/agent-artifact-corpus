import { createHash, timingSafeEqual } from "node:crypto";

export type AgentIdentity = {
  id: string;
  name: string;
};

export type Config = {
  port: number;
  publicBaseUrl: string;
  databaseUrl: string;
  agents: Array<AgentIdentity & { tokenHash: Buffer }>;
  debugGithubIds?: string[];
  githubOAuth?: {
    clientId: string;
    clientSecret: string;
    callbackUrl: string;
  };
};

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const tokenJson = env.AGENTS_CHAT_TOKENS_JSON ?? "{}";
  let tokens: Record<string, unknown>;
  try {
    tokens = JSON.parse(tokenJson) as Record<string, unknown>;
  } catch {
    throw new Error("AGENTS_CHAT_TOKENS_JSON must be a JSON object mapping bearer tokens to agent names");
  }
  const agents = Object.entries(tokens).map(([token, name]) => {
    if (token.length < 24 || typeof name !== "string" || name.trim().length < 1 || name.length > 64) {
      throw new Error("Each agent token must be at least 24 characters and each name must be 1-64 characters");
    }
    const tokenHash = digest(token);
    return { id: `agent_${tokenHash.toString("hex").slice(0, 20)}`, name: name.trim(), tokenHash };
  });
  const publicBaseUrl = (env.PUBLIC_BASE_URL ?? "http://localhost:3000").replace(/\/$/, "");
  const githubClientId = env.GITHUB_CLIENT_ID?.trim();
  const githubClientSecret = env.GITHUB_CLIENT_SECRET?.trim();
  const debugGithubIds = (env.AGENTS_CHAT_DEBUG_GITHUB_IDS ?? "").split(",").map((id) => id.trim()).filter(Boolean);
  if (debugGithubIds.some((id) => !/^[1-9]\d*$/.test(id))) {
    throw new Error("AGENTS_CHAT_DEBUG_GITHUB_IDS must contain comma-separated numeric GitHub account IDs");
  }
  if (Boolean(githubClientId) !== Boolean(githubClientSecret)) {
    throw new Error("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be configured together");
  }
  if (agents.length === 0 && !githubClientId) {
    throw new Error("Configure GitHub OAuth or at least one static agent token");
  }
  return {
    port: Number(env.PORT ?? "3000"),
    publicBaseUrl,
    databaseUrl: env.DATABASE_URL ?? "file:./data/agents-chat.sqlite",
    agents,
    debugGithubIds,
    ...(githubClientId && githubClientSecret ? {
      githubOAuth: {
        clientId: githubClientId,
        clientSecret: githubClientSecret,
        callbackUrl: `${publicBaseUrl}/oauth/github/callback`
      }
    } : {})
  };
}

export function authenticate(config: Config, authorization: string | undefined): AgentIdentity | null {
  if (!authorization?.startsWith("Bearer ")) return null;
  const candidate = digest(authorization.slice("Bearer ".length));
  for (const agent of config.agents) {
    if (candidate.length === agent.tokenHash.length && timingSafeEqual(candidate, agent.tokenHash)) {
      return { id: agent.id, name: agent.name };
    }
  }
  return null;
}

export function digest(value: string): Buffer {
  return createHash("sha256").update(value).digest();
}
