---
name: vlm-configuration
description: Configure the Vision Language Model (VLM) used for analyzing experiment plots. Use when the user asks to change the VLM provider or model, adjust temperature or max_tokens, enable or disable thinking mode, or troubleshoot VLM-related behavior in config.yaml.
---

# VLM Configuration

The VLM (Vision Language Model) is configured in `config.yaml` under the `vlm` section.

## Config Location

`config.yaml` (in the project root)

## Current Config Structure

```yaml
vlm:
  provider: "nvidia"
  model: "nvidia/ising-calibration-1-35b-a3b"
  api_key_env: "NVIDIA_API_KEY"
  temperature: 0.2
  max_tokens: 32768
  enable_thinking: false
```

## Supported Models (NVIDIA API)

| Model | Provider | Notes |
|-------|----------|-------|
| `nvidia/ising-calibration-1-35b-a3b` | NVIDIA | Default, fine-tuned for calibration |
| `google/gemma-4-31b-it` | Google | General-purpose 31B |
| `meta/llama-3.2-90b-vision-instruct` | Meta | Most capable |
| `meta/llama-3.2-11b-vision-instruct` | Meta | Balanced |
| `microsoft/phi-3.5-vision-instruct` | Microsoft | Lightweight |

## Environment Variables

The VLM uses `NVIDIA_API_KEY` (same key as the main LLM).

## To Change VLM

1. Read current config.yaml
2. Edit the `vlm` section with new values
3. Changes take effect immediately on next `vlm_inspect` call (no restart needed)
