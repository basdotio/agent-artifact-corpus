#!/usr/bin/env node
import { Command } from "commander";
import { OuraClient } from "./client.js";
import { runAuthFlow } from "./auth.js";
import { loadConfig, saveConfig, getConfigPath } from "./config.js";
import { today } from "./utils.js";
import { VERSION } from "./version.js";

const program = new Command();

program
  .name("oura")
  .description("Oura Ring CLI — query sleep, readiness, and activity data")
  .version(VERSION);

program
  .command("auth")
  .description("Run OAuth2 authorization flow")
  .action(async () => {
    await runAuthFlow();
  });

const configCmd = program
  .command("config")
  .description("Manage stored credentials (~/.oura-mcp/config.json)");

configCmd
  .command("set-token <token>")
  .description("Save a personal access token")
  .action((token: string) => {
    const config = loadConfig();
    config.token = token;
    saveConfig(config);
    console.log(`Token saved to ${getConfigPath()}`);
  });

configCmd
  .command("show")
  .description("Show current config (tokens are masked)")
  .action(() => {
    const config = loadConfig();
    const mask = (v: string | undefined) => v ? v.slice(0, 4) + "..." + v.slice(-4) : "(not set)";
    console.log(JSON.stringify({
      token: mask(config.token),
      accessToken: mask(config.accessToken),
      refreshToken: mask(config.refreshToken),
      clientId: mask(config.clientId),
      clientSecret: mask(config.clientSecret),
      path: getConfigPath(),
    }, null, 2));
  });

configCmd
  .command("clear")
  .description("Remove stored credentials")
  .action(() => {
    saveConfig({});
    console.log("Config cleared.");
  });

program
  .command("sleep")
  .description("Get daily sleep score and sleep periods")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const [daily, periods] = await Promise.all([
      client.getDailySleep(opts.date),
      client.getSleepPeriods(opts.date),
    ]);
    console.log(JSON.stringify({ daily, periods }, null, 2));
  });

program
  .command("readiness")
  .description("Get daily readiness score")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const readiness = await client.getDailyReadiness(opts.date);
    console.log(JSON.stringify(readiness, null, 2));
  });

program
  .command("activity")
  .description("Get daily activity data")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const activity = await client.getDailyActivity(opts.date);
    console.log(JSON.stringify(activity, null, 2));
  });

program
  .command("summary")
  .description("Get all data for a day (sleep, readiness, activity)")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const [sleep, readiness, sleepPeriods, activity] = await Promise.all([
      client.getDailySleep(opts.date),
      client.getDailyReadiness(opts.date),
      client.getSleepPeriods(opts.date),
      client.getDailyActivity(opts.date),
    ]);
    console.log(JSON.stringify({ date: opts.date, sleep, readiness, sleepPeriods, activity }, null, 2));
  });

program
  .command("workouts")
  .description("Get auto-detected workouts")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const workouts = await client.getWorkouts(opts.date);
    console.log(JSON.stringify(workouts, null, 2));
  });

program
  .command("heart-rate")
  .description("Get continuous heart rate data")
  .requiredOption("--start <datetime>", "Start datetime in ISO 8601 format")
  .requiredOption("--end <datetime>", "End datetime in ISO 8601 format")
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const hr = await client.getHeartRate(opts.start, opts.end);
    console.log(JSON.stringify(hr, null, 2));
  });

program
  .command("stress")
  .description("Get daily stress levels")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const stress = await client.getDailyStress(opts.date);
    console.log(JSON.stringify(stress, null, 2));
  });

program
  .command("spo2")
  .description("Get daily blood oxygen (SpO2)")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const spo2 = await client.getDailySpO2(opts.date);
    console.log(JSON.stringify(spo2, null, 2));
  });

program
  .command("sessions")
  .description("Get meditation/breathing sessions")
  .option("--date <date>", "Date in YYYY-MM-DD format", today())
  .action(async (opts) => {
    const client = OuraClient.fromEnv();
    const sessions = await client.getSessions(opts.date);
    console.log(JSON.stringify(sessions, null, 2));
  });

program.parseAsync().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
