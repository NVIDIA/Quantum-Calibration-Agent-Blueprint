# VLM Configuration

The VLM (Vision Language Model) is configured in `config.yaml` under the `vlm` section.

## Config Location

`config.yaml` (in the project root)

## Current Config Structure

```yaml
vlm:
  provider: "nvidia"
  model: "google/gemma-4-31b-it"
  api_key_env: "NVIDIA_API_KEY"
  temperature: 0
  max_tokens: 16384
```

## Supported Models (NVIDIA API)

| Model | Provider | Notes |
|-------|----------|-------|
| `google/gemma-4-31b-it` | Google | Default, 31B with thinking |
| `meta/llama-3.2-90b-vision-instruct` | Meta | Most capable |
| `meta/llama-3.2-11b-vision-instruct` | Meta | Balanced |
| `microsoft/phi-3.5-vision-instruct` | Microsoft | Lightweight |

## Environment Variables

The VLM uses `NVIDIA_API_KEY` (same key as the main LLM).

## To Change VLM

1. Read current config.yaml
2. Edit the `vlm` section with new values
3. Changes take effect immediately on next `vlm_inspect` call (no restart needed)
