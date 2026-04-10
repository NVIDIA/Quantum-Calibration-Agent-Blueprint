# QCA Documentation

Welcome to the NVIDIA Quantum Calibration Agent (QCA) documentation.

QCA is a quantum calibration agent built on the DeepAgents framework, providing an intelligent CLI and workflow system for running and managing quantum calibration experiments.

```{figure} /_static/images/usage/web-ui-overview.png
:alt: Web UI
:width: 100%

The Web UI provides a chat interface for natural language interaction with the calibration agent.
```

```{figure} /_static/images/usage/cli-banner.png
:alt: CLI Interface
:width: 100%

The CLI provides a terminal-based interface for quantum calibration experiments.
```

## Getting Started

New to QCA? Start here:

```{toctree}
:maxdepth: 2
:caption: Quick Start

quick-start/index
quick-start/installation
```

## User Guide

Learn how to use QCA effectively:

```{toctree}
:maxdepth: 2
:caption: User Guide

user-guide/index
user-guide/cli-overview
user-guide/configuration
user-guide/knowledge-base
user-guide/workflows/index
user-guide/experiments/index
```

## Developer Guide

Contributing to QCA? Read this:

```{toctree}
:maxdepth: 2
:caption: Developer Guide

developer-guide/index
developer-guide/architecture
developer-guide/contributing
```

## Key Features

- **Intelligent CLI**: Natural language interface powered by NVIDIA LLMs
- **Workflow System**: Define and execute multi-step calibration workflows
- **Experiment Management**: Discover, validate, and run quantum experiments
- **Data Storage**: HDF5-based storage with SQLite indexing
- **VLM Integration**: Visual inspection of calibration plots

## Quick Links

- [Installation](quick-start/installation.md)
- [CLI Overview](user-guide/cli-overview.md)
- [Workflow Guide](user-guide/workflows/index.md)

## License

QCA is released under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
