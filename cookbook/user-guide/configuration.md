# Configuration

QCA uses a two-part configuration system: environment variables for secrets and API keys, and a YAML file for application settings. This separation keeps sensitive credentials secure while making settings easy to manage.

## Quick Overview

**Two configuration sources:**

1. **`.env` file** - API keys and secrets (never commit this)
2. **`config.yaml`** - Application settings (version controlled)

**Common configurations:**
- Set up NVIDIA API key (required for AI features)
- Configure VLM for visual plot analysis (optional)
- Adjust server settings (optional)

## Environment Variables (.env)

Environment variables are loaded from a `.env` file in the project root. This file should never be committed to version control.

### Required Variables

```bash
# Scripts directory (required for experiment discovery)
QCAL_SCRIPTS_DIR=./scripts

# NVIDIA API Key (required)
# Used for the main AI agent (Nemotron models)
NVIDIA_API_KEY=nvapi-...
```

Without the NVIDIA API key, the AI-powered features of QCA will not work.

### Setting Up Your .env File

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```bash
   # Replace with your actual keys
   QCAL_SCRIPTS_DIR=./scripts
   NVIDIA_API_KEY=nvapi-...
   ```

3. Verify the file is in your `.gitignore` to prevent accidental commits:
   ```bash
   grep "^\.env$" .gitignore
   ```

## Configuration File (config.yaml)

The `config.yaml` file contains application settings. It is version controlled and should not contain secrets.

### Complete Example

```yaml
general:
  front_end:
    _type: fastapi
    host: "0.0.0.0"
    port: 8000
    workers: 1
    reload: true
    workflow:
      method: "POST"
      description: "Deep Agent workflow with filesystem and shell tools"
      path: "/generate"
      websocket_path: "/websocket"

# VLM (Vision Language Model) configuration
vlm:
  provider: "nvidia"
  model: "google/gemma-4-31b-it"
  api_key_env: "NVIDIA_API_KEY"
  temperature: 0
  max_tokens: 16384
```

### Configuration Sections

#### general.front_end

Server configuration for the FastAPI backend.

| Option | Default | Description |
|--------|---------|-------------|
| `_type` | `fastapi` | Server type (always fastapi) |
| `host` | `0.0.0.0` | Bind address (0.0.0.0 for all interfaces) |
| `port` | `8000` | HTTP port |
| `workers` | `1` | Number of worker processes |
| `reload` | `true` | Auto-reload on code changes (dev mode) |

**Workflow endpoints:**
- `workflow.path` - Main workflow endpoint (`/generate`)
- `workflow.websocket_path` - WebSocket endpoint (`/websocket`)

#### vlm

Vision Language Model configuration for the `vlm_inspect` tool.

| Option | Default | Description |
|--------|---------|-------------|
| `provider` | `nvidia` | VLM provider (nvidia or custom) |
| `model` | `google/gemma-4-31b-it` | Model identifier |
| `api_key_env` | `NVIDIA_API_KEY` | Environment variable for API key |
| `temperature` | `0` | Sampling temperature (0 = deterministic) |
| `max_tokens` | `16384` | Maximum response tokens |

## VLM Configuration

The VLM (Vision Language Model) is used for visual plot analysis via the `vlm_inspect` tool. It's optional but powerful for automated plot interpretation.

### Supported Models

QCA uses NVIDIA models via the NVIDIA API Catalog:

```yaml
vlm:
  provider: "nvidia"
  model: "google/gemma-4-31b-it"
  api_key_env: "NVIDIA_API_KEY"
  temperature: 0
  max_tokens: 16384
```

### VLM Setup Steps

1. Get an API key from [NVIDIA API Catalog](https://build.nvidia.com/)
2. Add the API key to `.env`:
   ```bash
   NVIDIA_API_KEY=nvapi-...
   ```
3. Configure `config.yaml`:
   ```yaml
   vlm:
     provider: "nvidia"
     model: "google/gemma-4-31b-it"
     api_key_env: "NVIDIA_API_KEY"
   ```
4. Test with:
   ```bash
   qca -n "Use vlm_inspect to analyze experiment <id>"
   ```

## Model Configuration

QCA supports multiple LLM providers through LiteLLM. You can use NVIDIA, Anthropic, OpenAI, or any other LiteLLM-compatible provider.

### Supported Providers

| Provider | Model Format | API Key Environment Variable |
|----------|--------------|------------------------------|
| NVIDIA | `nvidia:model-name` | `NVIDIA_API_KEY` |
| Anthropic | `anthropic:model-name` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai:model-name` | `OPENAI_API_KEY` |

### Configuration Methods

**Method 1: Environment Variable (Recommended)**

Set the `QCA_MODEL` environment variable in your `.env` file:

```bash
# Using NVIDIA (default)
NVIDIA_API_KEY=nvapi-your-key-here
QCA_MODEL=nvidia:nvidia/nemotron-3-nano-30b-a3b

# Using Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here
QCA_MODEL=anthropic:claude-sonnet-4-20250514

# Using OpenAI GPT
OPENAI_API_KEY=sk-your-key-here
QCA_MODEL=openai:gpt-4o
```

**Method 2: CLI Flag**

Override the model for a single command:

```bash
# Use Anthropic Claude
qca --model anthropic:claude-sonnet-4-20250514 -n "List experiments"

# Use OpenAI GPT-4o
qca --model openai:gpt-4o -n "Run qubit spectroscopy"

# Use NVIDIA Nemotron
qca --model nvidia:nvidia/nemotron-3-nano-30b-a3b -n "Analyze results"
```

### Popular Model Examples

**Anthropic:**
- `anthropic:claude-sonnet-4-20250514` - Claude Sonnet 4 (recommended)
- `anthropic:claude-opus-4-20250514` - Claude Opus 4

**OpenAI:**
- `openai:gpt-4o` - GPT-4o (recommended)
- `openai:gpt-4-turbo` - GPT-4 Turbo
- `openai:o1` - OpenAI o1

**NVIDIA:**
- `nvidia:nvidia/nemotron-3-nano-30b-a3b` - Nemotron 3 Nano 30B (default, 3B active)
- `nvidia:nvidia/nemotron-3-super-120b-a12b` - Nemotron 3 Super 120B

## Configuration Tips

### Development vs Production

**Development:**
```yaml
general:
  front_end:
    host: "127.0.0.1"    # Localhost only
    reload: true         # Auto-reload on changes
    workers: 1           # Single worker
```

**Production:**
```yaml
general:
  front_end:
    host: "0.0.0.0"      # All interfaces
    reload: false        # No auto-reload
    workers: 4           # Multiple workers
```

### Security Best Practices

1. **Never commit `.env`** - Always in `.gitignore`
2. **Rotate API keys** - Change keys periodically
3. **Use least privilege** - Only enable features you need
4. **Restrict server access** - Use `127.0.0.1` for local-only access

## Next Steps

- [CLI Overview](cli-overview.md) - Learn the command-line interface
- [Workflow System](workflows/index.md) - Create and run workflows
