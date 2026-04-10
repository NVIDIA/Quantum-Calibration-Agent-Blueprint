# User Guide

Welcome to the QCA User Guide. This guide provides comprehensive documentation for using QCA to run quantum calibration experiments, manage workflows, and analyze experimental data.

```{figure} /_static/images/usage/web-ui-overview.png
:alt: Web UI Overview
:width: 100%

The Web UI showing the chat interface, sidebar navigation, and panels.
```

## What's Covered

This user guide covers all aspects of using QCA:

- **CLI Overview**: Learn the `qca` command-line interface, including all subcommands and global options
- **Workflows**: Create and execute multi-step calibration workflows with dependency management
- **Experiments**: Run individual experiments, write custom experiment scripts, and manage experiment data
- **Knowledge Base**: Store and manage reusable documents, scripts, and calibration notes
- **Configuration**: Configure QCA behavior through config files and environment variables

## Quick Navigation

### Getting Started
- [CLI Overview](cli-overview.md) - Complete command-line reference and common usage patterns
- [Configuration](configuration.md) - Set up your environment and customize behavior

### Working with Experiments
- [Running Experiments](experiments/running-experiments.md) - Execute experiments via CLI
- [Writing Scripts](experiments/writing-scripts.md) - Create custom experiment scripts
- [Experiment Storage](experiments/experiment-storage.md) - Understand data storage and retrieval

### Workflow System
- [Workflow Overview](workflows/index.md) - Multi-step calibration workflows

### Knowledge Base
- [Knowledge Base](knowledge-base.md) - Manage documents, scripts, and calibration notes

## Prerequisites

Before using QCA, ensure you have:

1. **Python Environment**: Python 3.11 or later
2. **Installation**: QCA installed via `pip install -e .`
3. **Configuration**: `.env` file with required API keys (NVIDIA_API_KEY)

## Usage Patterns

QCA supports multiple usage patterns to fit different workflows:

### Interactive TUI
Launch the full text-based interface for conversational experiment control:
```bash
qca
```

### Non-Interactive Mode
Execute single tasks from the command line:
```bash
qca -n "Run qubit spectroscopy on Q0 from 4.9 to 5.1 GHz"
```

### Direct CLI Commands
Use specific subcommands for scripting and automation:
```bash
qca experiments list
qca experiments run qubit_spectroscopy --params '{"center_freq": 5.0, "span": 0.2, "num_points": 51}'
qca history list --last 10
```

## Common Tasks

Here are some common tasks and where to find help:

| Task | See Documentation |
|------|-------------------|
| List available experiments | [CLI Overview - experiments list](cli-overview.md#experiments-list) |
| Run a specific experiment | [Running Experiments](experiments/running-experiments.md) |
| View past results | [CLI Overview - history commands](cli-overview.md#history-commands) |
| Create a workflow | [Workflow Overview](workflows/index.md) |
| Monitor workflow progress | [CLI Overview - workflow status](cli-overview.md#workflow-status) |
| Extract experiment data | [CLI Overview - data commands](cli-overview.md#data-commands) |

## Getting Help

Every command supports the `--help` flag for detailed usage information:

```bash
qca --help                    # Main help
qca experiments --help        # Experiments subcommands
qca workflow --help           # Workflow subcommands
qca history --help            # History subcommands
qca data --help               # Data subcommands
```

## Next Steps

New users should start with the [CLI Overview](cli-overview.md) to understand the command structure, then proceed to:

1. [Running Experiments](experiments/running-experiments.md) to execute your first experiment
2. [Workflow Overview](workflows/index.md) to orchestrate multiple experiments
3. [Configuration](configuration.md) to customize QCA behavior
