# Repository Explorer

Spawn a sub-agent to explore another repository without polluting the current context.

## Usage

```
/repo <alias> "<prompt>"
```

Examples:
- `/repo pay-core "how is authentication implemented?"`
- `/repo data-lake "find the Glue table definitions"`

## Arguments

$ARGUMENTS

## Instructions

1. Parse the arguments to extract the repo alias (first word) and the prompt (remaining text, quotes optional)

2. Read `~/.claude/repos.json` to get the repository mappings

3. Look up the provided alias in the mappings:
   - If not found, list available aliases and ask the user to pick one
   - If found, get the full path

4. Use the Task tool to spawn an Explore agent:
   - Set `subagent_type` to `Explore`
   - Set the prompt to include:
     - The working directory path from repos.json
     - The user's question/prompt
     - Instruction to be concise and return only relevant findings
   - Use `model: haiku` for quick lookups, or `sonnet` for deeper analysis

5. Return a concise summary of what was found, including:
   - Key file paths (relative to the repo)
   - Brief explanation of findings
   - Code snippets only if directly relevant

Keep the response focused - the goal is minimal context pollution.
