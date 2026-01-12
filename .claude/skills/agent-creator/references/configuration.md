# Agent Configuration Reference

## Available Tools

### Core Tools
| Tool | Description |
|------|-------------|
| `Read` | Read files from filesystem |
| `Write` | Create new files |
| `Edit` | Modify existing files |
| `Bash` | Execute shell commands |
| `Glob` | Pattern-based file search |
| `Grep` | Content search with regex |

### Interaction Tools
| Tool | Description |
|------|-------------|
| `Task` | Spawn subagents (note: agents cannot spawn other agents) |
| `AskUserQuestion` | Ask user for clarification |
| `TodoWrite` | Manage task lists |

### Web Tools
| Tool | Description |
|------|-------------|
| `WebFetch` | Fetch and process URLs |
| `WebSearch` | Search the web |

### Notebook Tools
| Tool | Description |
|------|-------------|
| `NotebookEdit` | Edit Jupyter notebook cells |

### Tool Shortcuts
- **Read-only**: `Read, Grep, Glob` - For exploration/analysis agents
- **Full access**: Omit `tools` field to inherit all tools

## Models

| Value | Behavior |
|-------|----------|
| `sonnet` | Default. Balanced capability and speed |
| `opus` | Most capable. Use for complex reasoning |
| `haiku` | Fastest, cheapest. Use for simple tasks |
| `inherit` | Match parent conversation model |

## Permission Modes

| Mode | Behavior |
|------|----------|
| `default` | Standard permission prompts |
| `acceptEdits` | Auto-accept file edits |
| `dontAsk` | Auto-deny prompts (allowed tools still work) |
| `bypassPermissions` | Skip all permission checks (use with caution) |
| `plan` | Plan mode (read-only exploration) |

Parent's `bypassPermissions` takes precedence and cannot be overridden.

## Hooks Configuration

Hooks run shell commands at lifecycle events. Define in frontmatter:

```yaml
hooks:
  PreToolUse:
    - matcher: "ToolName"
      hooks:
        - type: command
          command: "./script.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./post-edit.sh"
  Stop:
    - hooks:
        - type: command
          command: "./cleanup.sh"
```

### Hook Events

| Event | Matcher | When |
|-------|---------|------|
| `PreToolUse` | Tool name | Before tool execution |
| `PostToolUse` | Tool name | After tool execution |
| `Stop` | (none) | When agent finishes |

### Hook Input

Hooks receive JSON via stdin with:
- `tool_name`: Name of the tool
- `tool_input`: Tool's input parameters (e.g., `tool_input.command` for Bash)

### Exit Codes

| Code | Behavior |
|------|----------|
| 0 | Allow operation |
| 2 | Block operation, feed stderr to Claude |
| Other | Error, operation continues |

### Validation Script Example

```bash
#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Block dangerous patterns
if echo "$COMMAND" | grep -iE '\b(rm -rf|DROP TABLE)\b' > /dev/null; then
  echo "Blocked: Dangerous operation" >&2
  exit 2
fi
exit 0
```

## Skills Field

Load skills into agent context at startup:

```yaml
skills: skill-name, another-skill
```

Skills provide the agent with additional procedural knowledge. The full skill content is injected at startup. Agents don't inherit skills from the parent conversation.

## Disabling Agents

Add to settings.json `permissions.deny`:

```json
{
  "permissions": {
    "deny": ["Task(agent-name)", "Task(Explore)"]
  }
}
```

Or via CLI:

```bash
claude --disallowedTools "Task(agent-name)"
```
