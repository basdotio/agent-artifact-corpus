#!/usr/bin/env npx tsx
/**
 * masterfabric-academy MCP
 *
 * Local stdio MCP server that guides learners through MasterFabric Academy
 * curricula (days/) with instructor + staff-engineer mentor personas, and
 * exposes the day-by-day academy skill for Cursor agents.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  dayTitle,
  getTrack,
  listAvailableDays,
  listTracks,
  parsePhases,
  phaseForDay,
  readDay,
  readRoadmap,
  readSkill,
  REPO_ROOT,
} from "./lib/curriculum.js";
import {
  composeMentorPrompt,
  DEFAULT_PERSONA_STACK,
  getPersona,
  PERSONAS,
  type PersonaId,
} from "./lib/persona.js";

const SERVER_NAME = "masterfabric-academy";
const SERVER_VERSION = "1.0.0";

function text(body: string) {
  return { content: [{ type: "text" as const, text: body }] };
}

function errorText(err: unknown) {
  const message = err instanceof Error ? err.message : String(err);
  return {
    content: [{ type: "text" as const, text: `Error: ${message}` }],
    isError: true as const,
  };
}

function buildSessionBrief(opts: {
  trackId: string;
  day: number;
  personaIds?: PersonaId[];
  learnerGoal?: string;
}): string {
  const track = getTrack(opts.trackId);
  const dayMd = readDay(opts.trackId, opts.day);
  const phase = phaseForDay(opts.trackId, opts.day);
  const skill = readSkill();
  const personas = opts.personaIds?.length
    ? opts.personaIds
    : DEFAULT_PERSONA_STACK;
  const mentor = composeMentorPrompt(personas);

  const nextDay =
    opts.day < track.days
      ? `After Definition of Done, move to day ${opts.day + 1}.`
      : "This is the final day — focus on capstone polish and demo readiness.";

  return `# Session brief — ${track.name} day ${opts.day}

## Learner intent
${opts.learnerGoal?.trim() || "Follow the official day plan and build production-minded habits."}

## Track
- **Track:** ${track.name} (\`${track.id}\`)
- **Duration:** ${track.days} days
- **Focus:** ${track.focus}
- **Target profile:** ${track.profile}
- **Day file:** \`days/${track.folder}/${opts.day}.md\`
- **Roadmap:** \`days/${track.folder}/${track.roadmapFile}\`
- **Repo root:** \`${REPO_ROOT}\`

## Current phase
${
  phase
    ? `- **Range:** ${phase.range}
- **Focus area:** ${phase.focusArea}
- **Content:** ${phase.content}
- **Goal:** ${phase.goal}`
    : "_No matching phase row parsed; use the roadmap file._"
}

## Cadence
1. Activate mentor stack (below).
2. Apply the academy skill workflow.
3. Complete Today's Tasks from the day lesson.
4. Run Definition of Done checks.
5. ${nextDay}

---

${mentor}

---

# Academy skill (loaded)

${skill}

---

# Day ${opts.day} lesson — ${dayTitle(dayMd)}

${dayMd}
`;
}

function createServer(): McpServer {
  const server = new McpServer({
    name: SERVER_NAME,
    version: SERVER_VERSION,
  });

  server.tool(
    "get_mentor_persona",
    "Return MasterFabric Academy mentor personas (lead instructor, staff engineer, security coach, delivery manager) as system prompts. Use at session start so the agent teaches as a senior engineering mentor.",
    {
      persona: z
        .enum([
          "all",
          "lead-instructor",
          "staff-engineer",
          "security-coach",
          "delivery-manager",
        ])
        .default("all")
        .describe("Which persona to load; 'all' composes the full mentor stack"),
    },
    async ({ persona }) => {
      try {
        if (persona === "all") {
          return text(composeMentorPrompt());
        }
        const p = getPersona(persona);
        return text(
          `# ${p.title}\n\n${p.summary}\n\n---\n\n${p.systemPrompt}`,
        );
      } catch (err) {
        return errorText(err);
      }
    },
  );

  server.tool(
    "get_academy_skill",
    "Load the single MasterFabric Academy skill (day-by-day curriculum workflow). Agents should call this to manage teaching sessions consistently.",
    {},
    async () => {
      try {
        return text(readSkill());
      } catch (err) {
        return errorText(err);
      }
    },
  );

  server.tool(
    "list_tracks",
    "List all MasterFabric Academy learning tracks with duration, focus, and target engineer profile.",
    {},
    async () => {
      const rows = listTracks().map(
        (t) =>
          `| ${t.id} | ${t.name} | ${t.days} | ${t.focus} | ${t.profile} |`,
      );
      return text(
        `# Tracks\n\n| id | name | days | focus | profile |\n|---|---|---:|---|---|\n${rows.join("\n")}`,
      );
    },
  );

  server.tool(
    "get_roadmap",
    "Read a track roadmap (phase table) and optionally return parsed 5-day phase blocks for planning.",
    {
      track: z
        .string()
        .describe("Track id, e.g. go, nextjs, flutter, ai-agents"),
      parsed: z
        .boolean()
        .default(true)
        .describe("If true, also return structured phase blocks"),
    },
    async ({ track, parsed }) => {
      try {
        const meta = getTrack(track);
        const md = readRoadmap(track);
        if (!parsed) {
          return text(`# ${meta.name} roadmap\n\n${md}`);
        }
        const phases = parsePhases(md);
        const phaseJson = JSON.stringify(phases, null, 2);
        return text(
          `# ${meta.name} roadmap\n\n## Parsed phases\n\`\`\`json\n${phaseJson}\n\`\`\`\n\n## Raw roadmap\n\n${md}`,
        );
      } catch (err) {
        return errorText(err);
      }
    },
  );

  server.tool(
    "get_day_lesson",
    "Read the official day lesson markdown for a track (e.g. days/go/1.md). Prefer this over inventing curriculum content.",
    {
      track: z.string().describe("Track id, e.g. go"),
      day: z.number().int().min(1).describe("Day number (1-based)"),
      include_phase: z
        .boolean()
        .default(true)
        .describe("Include the matching roadmap phase context"),
    },
    async ({ track, day, include_phase }) => {
      try {
        const meta = getTrack(track);
        const md = readDay(track, day);
        const header = `# ${meta.name} — Day ${day}\n\n**File:** \`days/${meta.folder}/${day}.md\`\n**Title:** ${dayTitle(md)}\n`;
        if (!include_phase) {
          return text(`${header}\n${md}`);
        }
        const phase = phaseForDay(track, day);
        const phaseBlock = phase
          ? `## Phase context (${phase.range})\n- Focus: ${phase.focusArea}\n- Content: ${phase.content}\n- Goal: ${phase.goal}\n\n`
          : "";
        return text(`${header}\n${phaseBlock}---\n\n${md}`);
      } catch (err) {
        return errorText(err);
      }
    },
  );

  server.tool(
    "list_days",
    "List available day numbers for a track (from markdown files on disk).",
    {
      track: z.string().describe("Track id, e.g. go"),
    },
    async ({ track }) => {
      try {
        const meta = getTrack(track);
        const days = listAvailableDays(track);
        return text(
          `# ${meta.name} days\n\nExpected: 1–${meta.days}\nAvailable files: ${days.length}\n\n${days.join(", ")}`,
        );
      } catch (err) {
        return errorText(err);
      }
    },
  );

  server.tool(
    "start_learning_session",
    "Primary entrypoint: compose mentor personas + academy skill + current day lesson into one session brief the agent should follow. Use when a learner wants to study (e.g. learn Go) and needs guided next steps.",
    {
      track: z
        .string()
        .default("go")
        .describe("Track id; default go"),
      day: z
        .number()
        .int()
        .min(1)
        .default(1)
        .describe("Current day number; default 1"),
      learner_goal: z
        .string()
        .optional()
        .describe("Optional free-text goal, e.g. 'I want to learn Go for backend APIs'"),
      personas: z
        .array(
          z.enum([
            "lead-instructor",
            "staff-engineer",
            "security-coach",
            "delivery-manager",
          ]),
        )
        .optional()
        .describe("Optional subset of personas; default is the full stack"),
    },
    async ({ track, day, learner_goal, personas }) => {
      try {
        const brief = buildSessionBrief({
          trackId: track,
          day,
          learnerGoal: learner_goal,
          personaIds: personas as PersonaId[] | undefined,
        });
        return text(brief);
      } catch (err) {
        return errorText(err);
      }
    },
  );

  server.tool(
    "guide_next_steps",
    "Given track + current day (+ optional completion notes), return a structured plan: finish today, definition of done, and what to do tomorrow — aligned to roadmap phases.",
    {
      track: z.string().describe("Track id"),
      day: z.number().int().min(1).describe("Current day"),
      completed: z
        .boolean()
        .default(false)
        .describe("Whether today's tasks are already done"),
      notes: z
        .string()
        .optional()
        .describe("Optional notes about blockers or what was finished"),
    },
    async ({ track, day, completed, notes }) => {
      try {
        const meta = getTrack(track);
        const md = readDay(track, day);
        const phase = phaseForDay(track, day);
        const title = dayTitle(md);
        const tomorrow = day < meta.days ? day + 1 : null;
        const tomorrowTitle = tomorrow
          ? dayTitle(readDay(track, tomorrow))
          : null;

        const plan = `# Next steps — ${meta.name} day ${day}

## Status
- Day: **${day}** — ${title}
- Completed: **${completed ? "yes" : "no"}**
${notes ? `- Notes: ${notes}` : ""}

## Phase
${
  phase
    ? `${phase.range} · ${phase.focusArea}\nGoal: ${phase.goal}`
    : "See roadmap."
}

## Do now
${
  completed
    ? `1. Quick recap: restate today's core idea in 2–3 sentences.\n2. Commit / note progress if working in a trainee project.\n3. Open day ${tomorrow ?? day} and skim Tomorrow's tasks before stopping.`
    : `1. Open \`days/${meta.folder}/${day}.md\` and complete **Today's Tasks** in order.\n2. Prefer small, compiling increments; run formatters/tests the day asks for.\n3. Apply secure + production habits from the mentor stack (no secrets, validate inputs, clear errors).\n4. Stop when Definition of Done from the academy skill is met — do not silently skip tasks.`
}

## Definition of Done (today)
- [ ] Today's Tasks finished (or explicitly deferred with reason)
- [ ] Learner can explain the day's key concept
- [ ] Code/notes are clean enough for a teammate to review
- [ ] Security smell-check done for the topic

## Tomorrow
${
  tomorrow
    ? `- Day **${tomorrow}**: ${tomorrowTitle}\n- Call \`start_learning_session\` with track=\`${meta.id}\` day=${tomorrow}`
    : "- Capstone complete — schedule a demo review and map gaps to revisit phases."
}

## Agent instruction
Stay in mentor persona. Load skill via \`get_academy_skill\` if the session is cold. Do not invent alternate days outside this repo.
`;
        return text(plan);
      } catch (err) {
        return errorText(err);
      }
    },
  );

  server.tool(
    "list_personas",
    "List available mentor personas and short summaries.",
    {},
    async () => {
      const lines = Object.values(PERSONAS).map(
        (p) => `- **${p.id}** — ${p.title}: ${p.summary}`,
      );
      return text(`# Personas\n\n${lines.join("\n")}`);
    },
  );

  return server;
}

async function main() {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `${SERVER_NAME} MCP v${SERVER_VERSION} running on stdio (repo: ${REPO_ROOT})`,
  );
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
