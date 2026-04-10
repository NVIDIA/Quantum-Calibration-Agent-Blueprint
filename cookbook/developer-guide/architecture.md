# NVIDIA Quantum Calibration Agent Architecture

This document describes the overall architecture of the NVIDIA Quantum Calibration Agent, including component structure, data flow, and key design decisions.

## Overview

The NVIDIA Quantum Calibration Agent is built on the DeepAgents framework to provide an AI-powered interface for quantum calibration experiments. The system combines:
- A CLI interface for direct user interaction
- Experiment execution framework for quantum experiments
- HDF5/SQLite storage for experiment data
- A workflow system for complex multi-step calibrations
- VLM (Vision Language Model) support for analyzing plots

## Component Architecture

```{mermaid}
graph TB
    subgraph UI["User Interface"]
        CLI["CLI (TUI)<br/>qca"]
        CMD["CLI Commands<br/>qca experiments"]
        API["API Server<br/>(FastAPI)"]
    end

    subgraph DA["DeepAgents Framework"]
        AGENT["<b>Agent System</b><br/>(Chat/Query)"]
        TOOLS["Agent Tools"]
    end

    subgraph QCAL["QCAL Core"]
        DISC["Discovery<br/>Scan/Validate/Schema"]
        RUN["Runner<br/>Execute/Simulated"]
        STOR["Storage<br/>HDF5/SQLite"]
    end

    subgraph EXT["External"]
        SCRIPTS["Scripts/<br/>experiments"]
        BACKEND["Experiment<br/>Backend"]
        DATA["Data<br/>Directory"]
    end

    CLI --> AGENT
    CMD --> AGENT
    API --> AGENT
    AGENT <--> TOOLS
    TOOLS --> DISC
    TOOLS --> RUN
    TOOLS --> STOR
    DISC --> SCRIPTS
    RUN --> BACKEND
    STOR --> DATA

    style UI fill:#fff,stroke:#76B900,stroke-width:2px
    style DA fill:#fff,stroke:#76B900,stroke-width:2px
    style QCAL fill:#fff,stroke:#76B900,stroke-width:2px
    style EXT fill:#e0e0e0,stroke:#5b5e5e,stroke-width:2px
    style CLI fill:#fff,stroke:#76B900,stroke-width:2px
    style CMD fill:#fff,stroke:#76B900,stroke-width:2px
    style API fill:#fff,stroke:#76B900,stroke-width:2px
    style AGENT fill:#76B900,stroke:#76B900,stroke-width:2px,color:#fff
    style TOOLS fill:#fff,stroke:#76B900,stroke-width:2px
    style DISC fill:#fff,stroke:#76B900,stroke-width:2px
    style RUN fill:#fff,stroke:#76B900,stroke-width:2px
    style STOR fill:#fff,stroke:#76B900,stroke-width:2px
    style SCRIPTS fill:#e0e0e0,stroke:#5b5e5e,stroke-width:2px
    style BACKEND fill:#e0e0e0,stroke:#5b5e5e,stroke-width:2px
    style DATA fill:#e0e0e0,stroke:#5b5e5e,stroke-width:2px
```
