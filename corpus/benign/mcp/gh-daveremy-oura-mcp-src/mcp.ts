#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { OuraClient } from "./client.js";
import { formatLocalDate, today } from "./utils.js";
import { VERSION } from "./version.js";

const server = new McpServer({ name: "oura", version: VERSION });
const client = OuraClient.fromEnv();

function text(data: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
}

const optDate = z.string().optional().describe("YYYY-MM-DD, defaults to today");

server.registerTool("oura_daily_summary", {
  title: "Daily Summary",
  description: "Get sleep score, readiness score, sleep details, and activity for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  const [sleep, readiness, periods, activity] = await Promise.all([
    client.getDailySleep(d),
    client.getDailyReadiness(d),
    client.getSleepPeriods(d),
    client.getDailyActivity(d),
  ]);
  return text({ date: d, sleep, readiness, sleepPeriods: periods, activity });
});

server.registerTool("oura_sleep", {
  title: "Sleep Details",
  description: "Get detailed sleep session data (duration, stages, HR, HRV) for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  const [daily, periods] = await Promise.all([
    client.getDailySleep(d),
    client.getSleepPeriods(d),
  ]);
  return text({ date: d, daily, periods });
});

server.registerTool("oura_readiness", {
  title: "Readiness Score",
  description: "Get readiness score and contributors for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  return text(await client.getDailyReadiness(d));
});

server.registerTool("oura_activity", {
  title: "Daily Activity",
  description: "Get daily activity data (steps, calories, distance) for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  return text(await client.getDailyActivity(d));
});

server.registerTool("oura_workouts", {
  title: "Workouts",
  description: "Get auto-detected workouts with HR, calories, duration, and intensity for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  return text(await client.getWorkouts(d));
});

server.registerTool("oura_heart_rate", {
  title: "Heart Rate",
  description: "Get continuous heart rate data for a time window. Useful for correlating with untracked workouts.",
  inputSchema: z.object({
    start_datetime: z.string().describe("Start datetime in ISO 8601 format (e.g. 2024-01-01T00:00:00+00:00)"),
    end_datetime: z.string().describe("End datetime in ISO 8601 format (e.g. 2024-01-01T23:59:59+00:00)"),
  }),
}, async ({ start_datetime, end_datetime }) => {

  return text(await client.getHeartRate(start_datetime, end_datetime));
});

server.registerTool("oura_stress", {
  title: "Daily Stress",
  description: "Get daily stress and recovery levels for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  return text(await client.getDailyStress(d));
});

server.registerTool("oura_spo2", {
  title: "Blood Oxygen (SpO2)",
  description: "Get daily blood oxygen (SpO2) percentage for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  return text(await client.getDailySpO2(d));
});

server.registerTool("oura_sessions", {
  title: "Sessions",
  description: "Get meditation, breathing, and relaxation sessions for a date",
  inputSchema: z.object({ date: optDate }),
}, async ({ date }) => {
  const d = date ?? today();

  return text(await client.getSessions(d));
});

server.registerTool("oura_trends", {
  title: "Multi-day Trends",
  description: "Get sleep and readiness scores for a date range",
  inputSchema: z.object({
    days: z.number().int().min(1).optional().describe("Number of days to look back (default 7)"),
  }),
}, async ({ days }) => {
  const n = days ?? 7;


  const now = new Date();
  const endDate = formatLocalDate(now);
  const start = new Date(now);
  start.setDate(start.getDate() - (n - 1));
  const startDate = formatLocalDate(start);

  const [sleepData, readinessData] = await Promise.all([
    client.getDailySleepRange(startDate, endDate),
    client.getDailyReadinessRange(startDate, endDate),
  ]);

  const sleepByDay = new Map(sleepData.map(s => [s.day, s]));
  const readinessByDay = new Map(readinessData.map(r => [r.day, r]));

  const results: Array<{ date: string; sleep_score: number | null; readiness_score: number | null }> = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const ds = formatLocalDate(d);
    results.push({
      date: ds,
      sleep_score: sleepByDay.get(ds)?.score ?? null,
      readiness_score: readinessByDay.get(ds)?.score ?? null,
    });
  }

  return text(results);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Oura MCP server error:", err);
  process.exit(1);
});
