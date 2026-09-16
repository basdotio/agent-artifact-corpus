#!/usr/bin/env bun

import { execSync, spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import puppeteer from "puppeteer-core";

const arg = process.argv[2];
const HOME = process.env["HOME"];
const CHROME_DIR = `$HOME/Library/Application Support/Google/Chrome Beta`;

// Auto-detect profile based on current working directory
function autoDetectProfile() {
	const cwd = process.cwd();
	if (cwd.startsWith(`${HOME}/personal`)) {
		return "Default";
	} else if (cwd.startsWith(`${HOME}/work`)) {
		return "Profile 1";
	}
	return null;
}

// Get profile email for display
function getProfileEmail(profileDir) {
	const prefsPath = join(CHROME_DIR, profileDir, "Preferences");
	if (!existsSync(prefsPath)) return null;
	try {
		const prefs = JSON.parse(readFileSync(prefsPath, "utf-8"));
		return prefs.account_info?.[0]?.email || null;
	} catch {
		return null;
	}
}

let profileToUse = null;

if (arg === "--help" || arg === "-h") {
	console.log("Usage: browser-start.js [--profile [name]]");
	console.log("\nOptions:");
	console.log("  (no args)           Start with fresh profile");
	console.log("  --profile           Auto-detect profile based on cwd:");
	console.log(
		"                        ~/personal/** -> Default (tnagengast@gmail.com)",
	);
	console.log(
		"                        ~/work/** -> Profile 1 (tom@cable.tech)",
	);
	console.log(
		"  --profile <name>    Use specific profile (e.g., 'Default', 'Profile 1')",
	);
	console.log("\nExamples:");
	console.log("  browser-start.js                    # Fresh profile");
	console.log("  browser-start.js --profile          # Auto-detect from cwd");
	console.log(
		'  browser-start.js --profile "Profile 2"  # Use specific profile',
	);
	process.exit(0);
}

if (arg === "--profile") {
	// Check if there's a profile name argument
	const profileName = process.argv[3];
	if (profileName) {
		profileToUse = profileName;
	} else {
		// Auto-detect based on cwd
		profileToUse = autoDetectProfile();
		if (!profileToUse) {
			console.error(
				"✗ Could not auto-detect profile. Use --profile <name> to specify.",
			);
			console.error("  Run with --help to see available options.");
			process.exit(1);
		}
	}
} else if (arg && arg !== "--profile") {
	console.error("✗ Unknown argument. Run with --help for usage.");
	process.exit(1);
}

// Kill existing Chrome
try {
	execSync("killall 'Google Chrome'", { stdio: "ignore" });
} catch {}

// Wait a bit for processes to fully die
await new Promise((r) => setTimeout(r, 1000));

// Setup profile directory
execSync("mkdir -p ~/.cache/scraping", { stdio: "ignore" });

if (profileToUse) {
	const sourceProfile = join(CHROME_DIR, profileToUse);

	if (!existsSync(sourceProfile)) {
		console.error(`✗ Profile "${profileToUse}" not found at ${sourceProfile}`);
		process.exit(1);
	}

	// Sync profile with rsync (much faster on subsequent runs)
	execSync(`rsync -a --delete "${sourceProfile}/" ~/.cache/scraping/Default/`, {
		stdio: "pipe",
	});

	const email = getProfileEmail(profileToUse);
	const displayInfo = email ? ` (${email})` : "";
	console.log(`Using profile: ${profileToUse}${displayInfo}`);
}

// Start Chrome in background (detached so Node can exit)
spawn(
	"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
	[
		"--remote-debugging-port=9222",
		`--user-data-dir=${process.env["HOME"]}/.cache/scraping`,
	],
	{ detached: true, stdio: "ignore" },
).unref();

// Wait for Chrome to be ready by attempting to connect
let connected = false;
for (let i = 0; i < 30; i++) {
	try {
		const browser = await puppeteer.connect({
			browserURL: "http://localhost:9222",
			defaultViewport: null,
		});
		await browser.disconnect();
		connected = true;
		break;
	} catch {
		await new Promise((r) => setTimeout(r, 500));
	}
}

if (!connected) {
	console.error("✗ Failed to connect to Chrome");
	process.exit(1);
}

if (!profileToUse) {
	console.log("✓ Chrome started on :9222 with fresh profile");
} else {
	console.log("✓ Chrome started on :9222");
}
