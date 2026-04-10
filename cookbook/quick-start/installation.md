# Installation

This guide covers installing QCA from source.

## Prerequisites

### Python Version

- **Python 3.11 or higher** (required)

Check your Python version:

```bash
python --version
```

If you need to install Python 3.11+, visit [python.org](https://www.python.org/downloads/).

### Node.js (for UI)

- **Node.js 18+** and **npm 9+** (required for the web UI)

Check your Node.js and npm versions:

```bash
node --version
npm --version
```

If you need to install Node.js, visit [nodejs.org](https://nodejs.org/).

## Install from Source

1. Clone the repository:

```bash
git clone https://github.com/NVIDIA/ising-calibration-agent-cookbook.git qca
cd qca
```

2. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install in editable mode:

```bash
pip install -e .
```

4. Verify installation:

```bash
qca --version
```

You should see output like:

```
qca 0.1.0
```

## Environment Configuration

### Set Up Scripts Path

QCA needs to know where experiment scripts are located:

```bash
# Set the scripts directory (required for experiment discovery)
export QCAL_SCRIPTS_DIR="$PWD/scripts"
```

### Set Up API Key

QCA requires NVIDIA API credentials for LLM functionality:

```bash
# Set your NVIDIA API key
export NVIDIA_API_KEY="your-nvidia-api-key"
```

Get your NVIDIA API key from [NVIDIA API Catalog](https://build.nvidia.com/).

### Create Environment File

For persistence, create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```bash
QCAL_SCRIPTS_DIR=./scripts
NVIDIA_API_KEY=nvapi-...
```

## Verify Installation

### Check Version

```bash
qca --version
```

### Test CLI Access

List available experiments:

```bash
qca experiments list
```

### Launch Interactive Mode

Start the terminal interface:

```bash
qca
```

You should see the QCA banner and welcome message. Type `exit` to quit.

```{figure} /_static/images/usage/cli-banner.png
:alt: QCA CLI
:width: 100%

The QCA command-line interface showing the welcome banner.
```

## Next Steps

- [User Guide](../user-guide/index.md) - Complete usage documentation
- [Configuration Guide](../user-guide/configuration.md) - Detailed configuration options
