# CLAUDE.md

Authoritative development guide — also see `AGENTS.md` for additional AI assistant instructions.

## Project Overview

Hermes Agent is a fully open-source AI agent harness. It provides an interactive TUI, multi-platform messaging gateway (Telegram, Discord, Slack, WhatsApp), scheduled automations, persistent memory/skills, and multiple sandboxed terminal backends (local, Docker, SSH, Singularity, Modal).

## Runtime & Package Manager

- Python 3.11+, managed with **uv** (lockfile pinned)
- Entry point: `hermes` CLI (symlinked via install script)
- PyPI package: `hermes-agent`

## Development Commands

```bash
# Always activate venv first
source venv/bin/activate

# Install
pip install -e .

# Run
hermes               # Interactive TUI
hermes setup         # First-time setup wizard
hermes doctor        # Diagnose configuration issues
hermes config check  # Validate config.yaml
hermes chat -q "test message"   # Quick one-shot test

# Tests
pytest tests/

# Update
hermes update
```

## Project Structure

```
run_agent.py              # AIAgent class — core conversation + tool dispatch loop
cli.py                    # HermesCLI orchestrator (interactive TUI)
api_server.py             # REST API server
batch_runner.py           # Parallel batch trajectory generation
model_tools.py            # Thin dispatch layer; imports tools/ via _discover_tools()
toolsets.py               # Tool groupings (core, research, etc.)
toolset_distributions.py  # Probabilistic tool selection for batch runs
hermes_constants.py       # Shared constants
hermes_state.py           # Global runtime state

agent/                    # Agent internals
  model_metadata.py       # Context lengths, token estimation
  context_compressor.py   # Auto context compression
  prompt_caching.py       # Anthropic prompt caching
  prompt_builder.py       # System prompt assembly
  display.py              # Spinner, tool preview formatting
  trajectory.py           # Trajectory saving (ShareGPT format)

hermes_cli/               # CLI subcommand implementations
  main.py                 # Entry point, command dispatcher
  commands.py             # Slash command definitions + autocomplete
  config.py               # Config management and migration
  setup.py                # Interactive setup wizard
  gateway.py              # Gateway process management
  skills_hub.py           # /skills slash command + CLI hub

tools/                    # Tool implementations
  registry.py             # Central registry — schemas, handlers, dispatch
  approval.py             # Dangerous command detection
  terminal_tool.py        # Terminal orchestration (sudo, lifecycle)
  todo_tool.py            # Task planning
  skills_tool.py          # Agent-facing skill list/view
  skills_hub.py           # Skills Hub source adapters
  skills_guard.py         # Security scanner for skills
  environments/           # Terminal backends
    base.py               # BaseEnvironment ABC
    local.py              # Local execution
    docker.py             # Docker container
    ssh.py                # SSH remote
    singularity.py        # Singularity/Apptainer
    modal.py              # Modal cloud

gateway/                  # Messaging platform adapters
  platforms/              # telegram, discord, slack, whatsapp

cron/                     # Cron scheduler

skills/                   # Bundled skill documents (agentskills.io format)

environments/             # Atropos RL training environments
mini-swe-agent/           # Submodule: mini SWE agent
tinker-atropos/           # Submodule: Atropos RL integration
```

## User Configuration (stored in `~/.hermes/`)

| File | Purpose |
|---|---|
| `config.yaml` | Model, terminal backend, toolsets, TTS, compression |
| `.env` | API keys (`OPENROUTER_API_KEY`, `OPENAI_BASE_KEY`, etc.) |
| `auth.json` | OAuth credentials (Nous Portal) |
| `SOUL.md` | Optional global agent persona |

## Adding a New Tool

1. Create `tools/my_tool.py` — implement handler, define schema, call `registry.register(...)` at module level
2. Add `"tools.my_tool"` to `_discover_tools()` in `model_tools.py`
3. Add tool name to appropriate toolset in `toolsets.py`
4. Optionally add env vars to `OPTIONAL_ENV_VARS` in `hermes_cli/config.py`

All tool handlers **must return a JSON string**. The registry wraps exceptions in `{"error": "..."}` automatically.

## Trajectory Format

Conversations save in ShareGPT format (`.jsonl`):
```json
{"from": "system", "value": "..."}
{"from": "human",  "value": "..."}
{"from": "gpt",    "value": "<think>...</think>\n<tool_call>{...}</tool_call>"}
{"from": "tool",   "value": "<tool_response>{...}</tool_response>"}
```

## Key Conventions

- Tools with agent-level state (`todo`, `memory`) are intercepted in `run_agent.py` before `handle_function_call()` — the registry holds their schemas but dispatch is handled inline
- Stateful tools require a `task_id` kwarg for session isolation
- Skills are user-managed only; the agent cannot install skills autonomously
- `tools/registry.py` has no internal imports — it is the dependency root; all other tool files import from it
- Never hardcode model names — use `hermes_constants.py` or the config
