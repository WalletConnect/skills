#!/usr/bin/env node
/**
 * Unified Dependabot Report — Generate & Deliver via Claude Agent SDK
 *
 * Reads SKILL.md as the agent's instructions, exposes tools for running
 * the Python report script, reading files, and posting to Slack.
 *
 * Usage:
 *   node security/dependabot-report/scripts/run-report.mjs <skill-dir> [--dry-run]
 *
 * Environment:
 *   ANTHROPIC_API_KEY  - Required for Claude Agent SDK
 *   GH_TOKEN           - Required for the Python report script (GitHub API)
 *   SLACK_WEBHOOK_URL  - Slack incoming webhook URL (optional in dry-run)
 */

import { readFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { execFileSync } from "node:child_process";
import { query, tool, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

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

let skillContent;
try {
  skillContent = readFileSync(skillPath, "utf-8");
} catch (err) {
  console.error(`Error reading SKILL.md: ${err.message}`);
  process.exit(1);
}

// Create MCP server with tools for the agent
const server = createSdkMcpServer({
  name: "report-tools",
  version: "1.0.0",
  tools: [
    // Tool 1: Run the Python report script
    tool(
      "generate_report",
      "Run the Dependabot report Python script. Returns stdout and the generated report content.",
      {
        output_path: z.string().describe("File path where the report should be written (e.g. ./report.md)"),
        extra_args: z.array(z.string()).optional().describe("Additional CLI arguments for the script"),
      },
      async (args) => {
        const cmdArgs = [scriptPath, "--output", args.output_path];
        if (args.extra_args) cmdArgs.push(...args.extra_args);

        try {
          const stdout = execFileSync("python3", cmdArgs, {
            encoding: "utf-8",
            timeout: 120_000,
            env: { ...process.env },
          });

          // Read the generated file back
          let reportContent = "";
          try {
            reportContent = readFileSync(resolve(args.output_path), "utf-8");
          } catch {
            reportContent = "(could not read output file)";
          }

          return {
            content: [
              { type: "text", text: `Script stdout:\n${stdout}\n\n---\nGenerated report:\n${reportContent}` },
            ],
          };
        } catch (err) {
          return {
            content: [{ type: "text", text: `Script failed: ${err.message}\n${err.stderr || ""}` }],
            isError: true,
          };
        }
      }
    ),

    // Tool 2: Read a file
    tool(
      "read_file",
      "Read the contents of a file.",
      {
        path: z.string().describe("File path to read"),
      },
      async (args) => {
        try {
          const content = readFileSync(resolve(args.path), "utf-8");
          return { content: [{ type: "text", text: content }] };
        } catch (err) {
          return {
            content: [{ type: "text", text: `Error reading file: ${err.message}` }],
            isError: true,
          };
        }
      }
    ),

    // Tool 3: Post to Slack
    tool(
      "send_slack_message",
      "Post a message to the configured Slack channel via webhook. Use Slack mrkdwn formatting.",
      {
        text: z.string().describe("The message text to post to Slack (supports Slack mrkdwn)"),
      },
      async (args) => {
        if (dryRun) {
          console.log("\n--- DRY RUN: Would post to Slack ---");
          console.log(args.text);
          console.log("--- End dry run ---\n");
          return {
            content: [{ type: "text", text: "Dry run: message logged but not sent." }],
          };
        }

        if (!webhookUrl) {
          return {
            content: [{ type: "text", text: "No SLACK_WEBHOOK_URL configured. Message not sent." }],
          };
        }

        try {
          const resp = await fetch(webhookUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: args.text }),
          });

          if (!resp.ok) {
            const body = await resp.text();
            return {
              content: [{ type: "text", text: `Slack API error (${resp.status}): ${body}` }],
              isError: true,
            };
          }

          return {
            content: [{ type: "text", text: "Message posted to Slack successfully." }],
          };
        } catch (err) {
          return {
            content: [{ type: "text", text: `Failed to post to Slack: ${err.message}` }],
            isError: true,
          };
        }
      }
    ),
  ],
});

// Build prompt
const prompt = [
  "Follow the skill instructions provided in your system prompt.",
  "Generate the Dependabot report to `./report.md`, then deliver a Slack summary.",
  "",
  "Steps:",
  '1. Use the `generate_report` tool with output_path "./report.md"',
  "2. Review the report content returned by the tool",
  "3. If there are critical/high alerts, use `send_slack_message` to post a concise summary",
  "4. If there are zero alerts, skip Slack and respond that all is clear",
].join("\n");

// Run the agent
console.log(`Skill dir: ${resolvedSkillDir}`);
console.log(`Python script: ${scriptPath}`);
if (dryRun) console.log("Mode: dry-run (Slack messages will be logged, not sent)");

try {
  let result = null;

  for await (const message of query({
    prompt,
    options: {
      model: "claude-sonnet-4-5-20250514",
      maxTurns: 10,
      maxBudgetUsd: 0.50,
      permissionMode: "bypassPermissions",
      allowDangerouslySkipPermissions: true,
      allowedTools: [
        "mcp__report-tools__generate_report",
        "mcp__report-tools__read_file",
        "mcp__report-tools__send_slack_message",
      ],
      mcpServers: { "report-tools": server },
      systemPrompt: skillContent,
    },
  })) {
    if (message.type === "result") {
      if (message.subtype === "success") {
        result = message;
        console.log(`\nAgent result: ${message.result}`);
        console.log(`Cost: $${message.total_cost_usd.toFixed(4)}`);
        console.log(`Turns: ${message.num_turns}`);
      } else {
        console.error(`Agent error: ${message.subtype}`);
        if (message.errors) console.error(message.errors);
        process.exit(1);
      }
    }
  }

  if (!result) {
    console.error("Agent finished without producing a result");
    process.exit(1);
  }
} catch (err) {
  console.error(`Agent SDK error: ${err.message}`);
  process.exit(1);
}
