#!/usr/bin/env node
/**
 * Dependabot Report — Generate & Deliver via Anthropic Messages API
 *
 * Reads SKILL.md for context, runs the Python report script, asks Claude
 * to compose a Slack summary, and posts it via webhook.
 *
 * Usage:
 *   node scripts/run-report.mjs <skill-dir> [--dry-run]
 *
 * Environment:
 *   ANTHROPIC_API_KEY  - Required for Claude API
 *   GH_TOKEN           - Required for the Python report script (GitHub API)
 *   SLACK_WEBHOOK_URL  - Slack incoming webhook URL (optional in dry-run)
 *   GITHUB_RUN_URL     - GitHub Actions run URL (optional, added to Slack message)
 */

import { readFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { execFileSync } from "node:child_process";
import Anthropic from "@anthropic-ai/sdk";

const skillDir = process.argv[2];
const dryRun = process.argv.includes("--dry-run");

if (!skillDir) {
  console.error("Usage: run-report.mjs <skill-dir> [--dry-run]");
  process.exit(1);
}

if (!process.env.ANTHROPIC_API_KEY) {
  console.error("Error: ANTHROPIC_API_KEY environment variable is required");
  process.exit(1);
}

const webhookUrl = process.env.SLACK_WEBHOOK_URL;
if (!webhookUrl && !dryRun) {
  console.warn("Warning: SLACK_WEBHOOK_URL not set. Slack delivery will be skipped.");
}

// Resolve paths
const resolvedSkillDir = resolve(skillDir);
const skillPath = join(resolvedSkillDir, "SKILL.md");
const scriptPath = join(resolvedSkillDir, "scripts", "dependabot_report.py");
const reportPath = resolve("./report.md");

let skillContent;
try {
  skillContent = readFileSync(skillPath, "utf-8");
} catch (err) {
  console.error(`Error reading SKILL.md: ${err.message}`);
  process.exit(1);
}

// --- Step 1: Run the Python report script ---
console.log(`Skill dir: ${resolvedSkillDir}`);
console.log(`Python script: ${scriptPath}`);
if (dryRun) console.log("Mode: dry-run (Slack messages will be logged, not sent)");

console.log("\n--- Generating report ---");
let scriptOutput;
try {
  scriptOutput = execFileSync("python3", [scriptPath, "--output", reportPath], {
    encoding: "utf-8",
    timeout: 300_000,
    env: { ...process.env },
  });
  console.log(scriptOutput);
} catch (err) {
  console.error(`Python script failed: ${err.message}`);
  if (err.stderr) console.error(err.stderr);
  process.exit(1);
}

// --- Step 2: Read the generated report ---
let reportContent;
try {
  reportContent = readFileSync(reportPath, "utf-8");
  console.log(`Report generated: ${reportPath} (${reportContent.length} chars)`);
} catch (err) {
  console.error(`Failed to read report: ${err.message}`);
  process.exit(1);
}

// --- Step 3: Ask Claude to compose a Slack summary ---
console.log("\n--- Composing Slack summary ---");

const client = new Anthropic();

const slackPrompt = [
  "You are a security reporting assistant. Below is a Dependabot security alerts report.",
  "Compose a concise Slack summary using Slack mrkdwn formatting.",
  "",
  "Guidelines:",
  "- Lead with total alert counts by severity (use emoji: \ud83d\udd34 critical, \ud83d\udfe0 high)",
  "- Highlight the top 3-5 most affected repos",
  "- Mention teams needing attention",
  "- Keep it under 2000 characters",
  "- If there are zero critical/high alerts, say all clear",
  "- Do NOT use markdown code fences — output raw Slack mrkdwn only",
  "- End with a link to the full report (see below)",
  "",
  process.env.GITHUB_RUN_URL
    ? `Full report & artifacts: ${process.env.GITHUB_RUN_URL}`
    : "",
  "",
  "---",
  "",
  reportContent,
].join("\n");

let slackMessage;
try {
  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 1024,
    system: skillContent,
    messages: [{ role: "user", content: slackPrompt }],
  });

  slackMessage = response.content
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("\n");

  console.log(`Summary composed (${slackMessage.length} chars)`);
  console.log(`API usage: ${response.usage.input_tokens} in / ${response.usage.output_tokens} out`);
} catch (err) {
  console.error(`Claude API error: ${err.message}`);
  process.exit(1);
}

// --- Step 4: Post to Slack ---
if (dryRun) {
  console.log("\n--- DRY RUN: Would post to Slack ---");
  console.log(slackMessage);
  console.log("--- End dry run ---");
  process.exit(0);
}

if (!webhookUrl) {
  console.log("\nNo SLACK_WEBHOOK_URL — skipping Slack delivery.");
  console.log("\n--- Slack message preview ---");
  console.log(slackMessage);
  process.exit(0);
}

console.log("\n--- Posting to Slack ---");
try {
  const resp = await fetch(webhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: slackMessage }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    console.error(`Slack API error (${resp.status}): ${body}`);
    process.exit(1);
  }

  console.log("Posted to Slack successfully.");
} catch (err) {
  console.error(`Failed to post to Slack: ${err.message}`);
  process.exit(1);
}
