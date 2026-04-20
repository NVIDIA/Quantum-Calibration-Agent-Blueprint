#!/usr/bin/env python3

# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""QCA - Quantum Calibration Agent CLI.

Commands:
    qca                            # Launch TUI (default)
    qca serve                      # Launch backend server
    qca -n "prompt"                # Non-interactive execution
    qca -r <thread_id>             # Resume conversation
    qca experiments list           # List available experiments
    qca experiments schema X       # Show experiment schema
    qca experiments validate <path> # Validate script as experiment
    qca experiments run X          # Run an experiment
    qca history list               # List past experiments
    qca history show <id>          # Show experiment details
    qca data arrays <id>           # List arrays in experiment
    qca data get <id> <array>      # Get array data
    qca workflow list              # List all workflows
    qca workflow show <id>         # Show workflow definition
    qca workflow status <id>       # Show runtime progress
    qca workflow validate <id>     # Validate workflow structure
    qca workflow history <id>      # Show execution history
    qca workflow nodes <id>        # List nodes with state
    qca workflow watch <id>        # Live-watch progress
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

__version__ = "0.1.0"

# Default model for QCA
DEFAULT_MODEL = os.environ.get("QCA_MODEL", "nvidia:nvidia/nemotron-3-nano-30b-a3b")


def create_chat_model(model_name: str):
    """Create chat model based on provider.

    Uses official langchain-nvidia-ai-endpoints for NVIDIA models,
    init_chat_model for other providers.
    """
    if model_name.startswith("nvidia:"):
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(
            model=model_name[7:],  # strip "nvidia:" prefix
            api_key=os.environ.get("NVIDIA_API_KEY"),
            disable_streaming=True,  # NVIDIA has truncation bug with streaming
        )
    else:
        from langchain.chat_models import init_chat_model
        params = {}
        if model_name.startswith("openai:"):
            params["use_responses_api"] = False
        return init_chat_model(model_name, **params)

# Rich console for output
console = Console()

# =============================================================================
# Custom Branding
# =============================================================================

_UNICODE_BANNER = f"""
 ██████╗   ██████╗   █████╗        ╭───╮
██╔═══██╗ ██╔════╝  ██╔══██╗     ╭─┤ ◉ ├─╮
██║   ██║ ██║       ███████║    ─┤ ╰─┬─╯ ├─
██║▄▄ ██║ ██║       ██╔══██║     ╰─╮ │ ╭─╯
╚██████╔╝ ╚██████╗  ██║  ██║       ╰─┴─╯
 ╚══▀▀═╝   ╚═════╝  ╚═╝  ╚═╝

 Quantum Calibration Agent                       v{__version__}
"""

_ASCII_BANNER = f"""
  ___    ____    _                 .---.
 / _ \\  / ___|  / \\              .-' @ '-.
| | | || |     / _ \\            :   |   :
| |_| || |___ / ___ \\            '-. | .-'
 \\__\\_\\ \\____/_/   \\_\\             '---'

 Quantum Calibration Agent                     v{__version__}
"""


def _patch_banner():
    """Patch deepagents-cli banner."""
    from deepagents_cli import config

    def get_qca_banner() -> str:
        if config._detect_charset_mode() == config.CharsetMode.ASCII:
            return _ASCII_BANNER
        return _UNICODE_BANNER

    config.get_banner = get_qca_banner


def _patch_colors():
    """Patch deepagents-cli colors for NVIDIA green style with purple tools."""
    from deepagents_cli import config
    from textual.content import Content
    from textual.theme import Theme, BUILTIN_THEMES

    # Color palette
    TOOL_COLOR = "#c084fc"  # Light purple (violet-400) for tools
    NVIDIA_GREEN = "#10b981"  # Emerald green (deepagents-cli default)

    # Create custom theme based on textual-dark with NVIDIA green as primary
    dark_theme = BUILTIN_THEMES["textual-dark"]
    qca_theme = Theme(
        name="qca-dark",
        primary=NVIDIA_GREEN,
        secondary=dark_theme.secondary,
        accent=dark_theme.accent,
        success=NVIDIA_GREEN,  # Also make success green for ask-user menu
        warning=TOOL_COLOR,  # Purple for tool-related warnings
        error=dark_theme.error,
        surface=dark_theme.surface,
        panel=dark_theme.panel,
        background=dark_theme.background,
        boost=dark_theme.boost,
        dark=True,
    )

    # Patch DeepAgentsApp __init__ to register and apply custom theme
    from deepagents_cli.app import DeepAgentsApp
    _original_init = DeepAgentsApp.__init__
    def _patched_init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        self.register_theme(qca_theme)
        self.theme = "qca-dark"
    DeepAgentsApp.__init__ = _patched_init

    # Patch theme constants for primary/tool colors
    from deepagents_cli import theme
    theme.PRIMARY = NVIDIA_GREEN
    theme.TOOL_HEADER = TOOL_COLOR

    # Patch loading.py spinner color - both CSS and Python
    from deepagents_cli.widgets import loading

    # Patch the DEFAULT_CSS to use our color instead of $warning
    loading.LoadingWidget.DEFAULT_CSS = loading.LoadingWidget.DEFAULT_CSS.replace(
        "color: $warning;", f"color: {TOOL_COLOR};"
    )

    def _patched_update_animation(self):
        if self._paused:
            return
        if self._spinner_widget:
            frame = self._spinner.next_frame()
            self._spinner_widget.update(Content.styled(frame, TOOL_COLOR))
        if self._hint_widget and self._start_time is not None:
            from time import time
            elapsed = int(time() - self._start_time)
            self._hint_widget.update(f"({elapsed}s, esc to interrupt)")
    loading.LoadingWidget._update_animation = _patched_update_animation

    # Patch messages.py - tool header, file colors, @ mentions, borders
    from deepagents_cli.widgets import messages

    # Patch ToolCallMessage header
    _original_tool_compose = messages.ToolCallMessage.compose
    def _patched_tool_compose(self):
        from deepagents_cli.widgets.messages import format_tool_display
        from textual.widgets import Static
        tool_label = format_tool_display(self._tool_name, self._args)
        yield Static(
            Content.from_markup(
                f"[bold {TOOL_COLOR}]$label[/bold {TOOL_COLOR}]", label=tool_label
            ),
            classes="tool-header",
        )
        gen = _original_tool_compose(self)
        next(gen, None)  # Skip the original header
        yield from gen
    messages.ToolCallMessage.compose = _patched_tool_compose

    # Patch UserMessage DEFAULT_CSS - border color
    messages.UserMessage.DEFAULT_CSS = messages.UserMessage.DEFAULT_CSS.replace(
        "#10b981", NVIDIA_GREEN
    )

    # Patch AssistantMessage DEFAULT_CSS if it has emerald
    if hasattr(messages, 'AssistantMessage'):
        messages.AssistantMessage.DEFAULT_CSS = messages.AssistantMessage.DEFAULT_CSS.replace(
            "#10b981", NVIDIA_GREEN
        )

    # Patch ToolCallMessage DEFAULT_CSS
    messages.ToolCallMessage.DEFAULT_CSS = messages.ToolCallMessage.DEFAULT_CSS.replace(
        "#10b981", NVIDIA_GREEN
    ).replace(
        "#f59e0b", TOOL_COLOR  # Orange tool status -> purple
    )

    # Patch _format_ls_output to use NVIDIA green instead of blue for .py files
    def _patched_format_ls_output(self, output: str, *, is_preview: bool = False):
        import ast
        from pathlib import Path
        from deepagents_cli.widgets.messages import FormattedOutput

        # Parse string output to list (same as original)
        try:
            items = ast.literal_eval(output)
            if not isinstance(items, list):
                return FormattedOutput(content=Content(output))
        except (ValueError, SyntaxError):
            return FormattedOutput(content=Content(output))

        lines = []
        max_items = 5 if is_preview else len(items)
        for item in items[:max_items]:
            path = Path(str(item))
            name = path.name
            if path.suffix in {".py", ".pyx"}:
                lines.append(Content.styled(f"    {name}", NVIDIA_GREEN))  # Was blue
            elif path.suffix in {".json", ".yaml", ".yml", ".toml"}:
                lines.append(Content.styled(f"    {name}", TOOL_COLOR))  # Was orange
            elif not path.suffix:
                lines.append(Content.styled(f"    {name}/", NVIDIA_GREEN))
            else:
                lines.append(Content(f"    {name}"))
        truncation = None
        if is_preview and len(items) > max_items:
            truncation = f"{len(items) - max_items} more"
        return FormattedOutput(content=Content("\n").join(lines), truncation=truncation)
    messages.ToolCallMessage._format_ls_output = _patched_format_ls_output

    # Patch approval.py command display color
    from deepagents_cli.widgets import approval

    def _patched_get_command_display(self, *, expanded: bool) -> Content:
        from deepagents_cli.config import get_glyphs
        from deepagents_cli.widgets.approval import (
            _SHELL_COMMAND_TRUNCATE_LENGTH, _WARNING_TEXT_TRUNCATE_LENGTH,
            strip_dangerous_unicode, detect_dangerous_unicode,
            render_with_unicode_markers, summarize_issues,
        )
        if not self._action_requests:
            raise RuntimeError("_get_command_display called with empty action_requests")
        req = self._action_requests[0]
        command_raw = str(req.get("args", {}).get("command", ""))
        command = strip_dangerous_unicode(command_raw)
        issues = detect_dangerous_unicode(command_raw)

        if expanded or len(command) <= _SHELL_COMMAND_TRUNCATE_LENGTH:
            command_display = command
        else:
            command_display = command[:_SHELL_COMMAND_TRUNCATE_LENGTH] + get_glyphs().ellipsis

        if not expanded and len(command) > _SHELL_COMMAND_TRUNCATE_LENGTH:
            display = Content.from_markup(
                f"[bold {TOOL_COLOR}]$cmd[/bold {TOOL_COLOR}] [dim](press 'e' to expand)[/dim]",
                cmd=command_display,
            )
        else:
            display = Content.from_markup(
                f"[bold {TOOL_COLOR}]$cmd[/bold {TOOL_COLOR}]", cmd=command_display
            )

        if not issues:
            return display

        raw_with_markers = render_with_unicode_markers(command_raw)
        if not expanded and len(raw_with_markers) > _WARNING_TEXT_TRUNCATE_LENGTH:
            raw_with_markers = raw_with_markers[:_WARNING_TEXT_TRUNCATE_LENGTH] + get_glyphs().ellipsis

        return Content.assemble(
            display,
            Content.from_markup(
                "\n[yellow]Warning:[/yellow] hidden chars detected ($summary)\n"
                "[dim]raw: $raw[/dim]",
                summary=summarize_issues(issues),
                raw=raw_with_markers,
            ),
        )
    approval.ApprovalMenu._get_command_display = _patched_get_command_display

    # Patch status.py colors
    from deepagents_cli.widgets import status
    if hasattr(status, 'StatusBar'):
        status.StatusBar.DEFAULT_CSS = status.StatusBar.DEFAULT_CSS.replace(
            "#10b981", NVIDIA_GREEN
        )

    # Patch DeepAgentsApp CSS overrides
    from deepagents_cli.app import DeepAgentsApp

    _original_css = getattr(DeepAgentsApp, 'CSS', '')
    DeepAgentsApp.CSS = _original_css + f"""
    /* Approval menu - purple for tool actions */
    .approval-menu {{
        border: solid {TOOL_COLOR};
    }}
    .approval-menu .approval-title {{
        color: {TOOL_COLOR};
    }}
    .approval-menu .approval-separator {{
        color: {TOOL_COLOR};
    }}

    /* Override $primary with NVIDIA green */
    ChatInput {{
        border: solid {NVIDIA_GREEN};
    }}
    ChatInput:focus {{
        border: solid {NVIDIA_GREEN};
    }}
    .chat-input-container {{
        border: solid {NVIDIA_GREEN};
    }}

    /* Ask user menu - NVIDIA green */
    .ask-user-menu {{
        border: solid {NVIDIA_GREEN};
    }}
    .ask-user-menu .ask-user-title {{
        color: {NVIDIA_GREEN};
    }}
    .ask-user-menu .ask-user-question-active {{
        border-left: thick {NVIDIA_GREEN};
    }}
    """


def _patch_welcome():
    """Patch deepagents-cli welcome message."""
    from deepagents_cli.widgets import welcome

    def _qca_build_welcome_footer(*, primary_color: str = "#10b981", tip=None):
        import random
        from textual.content import Content
        from deepagents_cli.widgets.welcome import _TIPS

        if tip is None:
            tip = random.choice(_TIPS)
        return Content.assemble(
            (
                "\nReady to calibrate! What quantum experiment shall we run?\n",
                primary_color,
            ),
            (f"Tip: {tip}", "dim italic"),
        )

    welcome.build_welcome_footer = _qca_build_welcome_footer


def _patch_project_paths():
    """Patch deepagents-cli to use .qca instead of .deepagents for project paths."""
    from deepagents_cli import config, project_utils

    def _qca_project_skills_dir(self):
        if self.project_root is None:
            return None
        return self.project_root / ".qca" / "skills"

    def _qca_project_agents_dir(self):
        if self.project_root is None:
            return None
        return self.project_root / ".qca" / "agents"

    project_utils.ProjectContext.project_skills_dir = _qca_project_skills_dir
    project_utils.ProjectContext.project_agents_dir = _qca_project_agents_dir

    def _qca_find_project_agent_md(project_root):
        candidates = [
            project_root / ".qca" / "AGENTS.md",
            project_root / "AGENTS.md",
        ]
        return [c for c in candidates if c.exists()]

    project_utils.find_project_agent_md = _qca_find_project_agent_md

    def _qca_settings_get_project_skills_dir(self):
        if not self.project_root:
            return None
        return self.project_root / ".qca" / "skills"

    def _qca_settings_get_project_agents_dir(self):
        if not self.project_root:
            return None
        return self.project_root / ".qca" / "agents"

    config.Settings.get_project_skills_dir = _qca_settings_get_project_skills_dir
    config.Settings.get_project_agents_dir = _qca_settings_get_project_agents_dir


# =============================================================================
# Directory Helpers
# =============================================================================


def get_scripts_dir() -> Path:
    """Get scripts directory."""
    env_dir = os.getenv("QCAL_SCRIPTS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent / "scripts"


def get_data_dir() -> Path:
    """Get data directory."""
    env_dir = os.getenv("QCAL_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent / "data"


# =============================================================================
# Typer App Definition
# =============================================================================

app = typer.Typer(
    name="qca",
    help="QCA - Quantum Calibration Agent",
    no_args_is_help=False,
    invoke_without_command=True,
)

experiments_app = typer.Typer(help="Experiment discovery and execution")
history_app = typer.Typer(help="Experiment history management")
data_app = typer.Typer(help="Data access and analysis")
workflow_app = typer.Typer(help="Workflow management and monitoring")

app.add_typer(experiments_app, name="experiments")
app.add_typer(history_app, name="history")
app.add_typer(data_app, name="data")
app.add_typer(workflow_app, name="workflow")


# =============================================================================
# Main Command (TUI / Non-interactive)
# =============================================================================


def _timestamp() -> str:
    """Return current timestamp string for non-interactive output."""
    from datetime import datetime
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def _format_tool_input(tool_input: dict, truncate: bool = True) -> str:
    """Format tool input for display."""
    if not tool_input:
        return ""
    # Show key=value pairs, optionally truncate long values
    parts = []
    for key, value in tool_input.items():
        if truncate and isinstance(value, str) and len(value) > 50:
            value = value[:47] + "..."
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def _format_tool_output(output: any, truncate: bool = True) -> str:
    """Format tool output summary for display."""
    if output is None:
        return "no output"

    # Handle ToolMessage objects
    if hasattr(output, "content"):
        output = output.content

    if isinstance(output, str):
        if truncate and len(output) > 100:
            return output[:97] + "..."
        return output
    if isinstance(output, dict):
        # Extract key info from common patterns
        if "status" in output:
            status = output.get("status", "")
            if "error" in output:
                err = output['error']
                if truncate and len(err) > 50:
                    err = err[:47] + "..."
                return f"status={status}, error={err}"
            return f"status={status}"
        if "error" in output:
            err = output['error']
            if truncate and len(err) > 50:
                err = err[:47] + "..."
            return f"error: {err}"
        # Show first few keys
        keys = list(output.keys())[:3]
        if len(output) > 3:
            return f"keys: {keys} (+{len(output)-3} more)"
        return f"keys: {keys}"
    result = str(output)
    if truncate and len(result) > 100:
        return result[:97] + "..."
    return result


async def _run_non_interactive(
    agent, message: str, *, quiet: bool = False, verbose: bool = False, stream: bool = True
) -> int:
    """Run a local agent non-interactively and print the response.

    Args:
        agent: Compiled LangGraph agent with QCA tools.
        message: The user message to process.
        quiet: Only output agent text to stdout.
        verbose: Show detailed tool inputs and outputs.
        stream: Stream tokens as they arrive.

    Returns:
        Exit code (0 success, 1 error).
    """
    import sys
    import uuid
    import time

    config = {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "recursion_limit": 1000,
    }
    inputs = {"messages": [{"role": "user", "content": message}]}

    # Track if we need to print timestamp at start of next content
    need_timestamp = True
    # Track tool start times for duration
    tool_start_times: dict[str, float] = {}

    try:
        if stream:
            async for event in agent.astream_events(
                inputs, config=config, version="v2"
            ):
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        # Handle both string content and list of content blocks
                        raw_content = chunk.content
                        if isinstance(raw_content, str):
                            content = raw_content
                        elif isinstance(raw_content, list):
                            # Extract text from content blocks
                            content = "".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in raw_content
                            )
                        else:
                            content = ""
                        if content:
                            # Add timestamp at start of new content after newline
                            if need_timestamp and content.strip():
                                sys.stdout.write(f"{_timestamp()} ")
                                need_timestamp = False
                            # Check if content ends with newline (next chunk needs timestamp)
                            if content.endswith("\n"):
                                need_timestamp = True
                            sys.stdout.write(content)
                            sys.stdout.flush()
                elif kind == "on_tool_start" and not quiet:
                    tool_name = event.get("name", "")
                    run_id = event.get("run_id", "")
                    tool_input = event.get("data", {}).get("input", {})
                    tool_start_times[run_id] = time.time()

                    # Always show inputs, verbose=full output (no truncation)
                    input_str = _format_tool_input(tool_input, truncate=not verbose)
                    if input_str:
                        sys.stderr.write(f"{_timestamp()} \U0001f527 Calling tool: {tool_name}\n")
                        sys.stderr.write(f"           \u2192 {input_str}\n")
                    else:
                        sys.stderr.write(f"{_timestamp()} \U0001f527 Calling tool: {tool_name}\n")
                    need_timestamp = True
                elif kind == "on_tool_end" and not quiet:
                    tool_name = event.get("name", "")
                    run_id = event.get("run_id", "")
                    output = event.get("data", {}).get("output")

                    duration = ""
                    if run_id in tool_start_times:
                        elapsed = time.time() - tool_start_times.pop(run_id)
                        duration = f" ({elapsed:.1f}s)"

                    # Always show output, verbose=full output (no truncation)
                    output_str = _format_tool_output(output, truncate=not verbose)
                    sys.stderr.write(f"{_timestamp()} \u2714 {tool_name} completed{duration}: {output_str}\n")
                    need_timestamp = True
            sys.stdout.write("\n")
        else:
            result = await agent.ainvoke(inputs, config=config)
            final = result.get("messages", [])
            if final:
                last = final[-1]
                content = getattr(last, "content", str(last))
                # Add timestamp to each line
                lines = content.split("\n")
                for line in lines:
                    if line.strip():
                        sys.stdout.write(f"{_timestamp()} {line}\n")
                    else:
                        sys.stdout.write("\n")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        sys.stderr.write(f"{_timestamp()} Error: {e}\n")
        return 1


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    non_interactive: Optional[str] = typer.Option(
        None,
        "-n",
        "--non-interactive",
        help="Run a single task non-interactively and exit",
    ),
    message: Optional[str] = typer.Option(
        None, "-m", "--message", help="Initial prompt to auto-submit when TUI starts"
    ),
    resume: Optional[str] = typer.Option(
        None, "-r", "--resume", help="Resume conversation by thread ID"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help=f"Model to use (default: {DEFAULT_MODEL})"
    ),
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Only output agent response to stdout (for piping)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Show full untruncated tool inputs and outputs"
    ),
    no_stream: bool = typer.Option(
        False, "--no-stream", help="Buffer full response before output"
    ),
    auto_approve: bool = typer.Option(
        False,
        "-y",
        "--auto-approve",
        help="Auto-approve all tool calls without prompting",
    ),
    version: bool = typer.Option(
        False, "-v", "--version", help="Show version and exit"
    ),
):
    """
    Quantum Calibration Agent.

    If no subcommand is provided, launches the interactive TUI.

    Examples:
        qca                              # Launch TUI
        qca -n "List experiments"        # Non-interactive
        qca -r abc123                    # Resume thread
        qca -m "Run spectroscopy"        # TUI with initial prompt
        qca experiments list             # List available experiments
    """
    if version:
        print(f"qca {__version__}")
        raise typer.Exit(0)

    # Only run if no subcommand was invoked
    if ctx.invoked_subcommand is not None:
        return

    # Apply patches
    _patch_banner()
    _patch_colors()
    _patch_welcome()
    _patch_project_paths()

    # Validate flags
    if (quiet or no_stream or verbose) and not non_interactive:
        console.print("[red]Error:[/red] --quiet, --verbose, and --no-stream require -n")
        raise typer.Exit(2)

    if non_interactive:
        # Non-interactive mode — use local agent with custom tools
        from deepagents_cli.agent import create_cli_agent
        from langgraph.checkpoint.memory import InMemorySaver

        from prompt import load_system_prompt
        from tools import find, lab, run_experiment, vlm_inspect, workflow

        tools = [find, lab, run_experiment, vlm_inspect, workflow]

        effective_model = model or DEFAULT_MODEL
        chat_model = create_chat_model(effective_model)

        agent, _backend = create_cli_agent(
            model=chat_model,
            assistant_id="qca",
            tools=tools,
            system_prompt=load_system_prompt(),
            checkpointer=InMemorySaver(),
            interactive=False,
            auto_approve=True,
        )

        exit_code = asyncio.run(
            _run_non_interactive(
                agent, non_interactive, quiet=quiet, verbose=verbose, stream=not no_stream
            )
        )
        raise typer.Exit(exit_code)
    else:
        # Interactive TUI mode
        from deepagents_cli.agent import create_cli_agent
        from deepagents_cli.app import DeepAgentsApp
        from langgraph.checkpoint.memory import InMemorySaver

        from prompt import load_system_prompt
        from tools import find, lab, run_experiment, vlm_inspect, workflow

        tools = [find, lab, run_experiment, vlm_inspect, workflow]

        effective_model = model or DEFAULT_MODEL
        chat_model = create_chat_model(effective_model)

        agent, backend = create_cli_agent(
            model=chat_model,
            assistant_id="qca",
            tools=tools,
            system_prompt=load_system_prompt(),
            checkpointer=InMemorySaver(),
        )

        app_instance = DeepAgentsApp(
            agent=agent,
            assistant_id="qca",
            backend=backend,
            initial_prompt=message,
            auto_approve=auto_approve,
            thread_id=resume,
            cwd=Path.cwd(),
        )
        app_instance.run()


# =============================================================================
# Experiments Commands
# =============================================================================


@experiments_app.command("list")
def experiments_list(
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """List all available experiments."""
    from core import discovery

    scripts_dir = get_scripts_dir()

    try:
        experiments = discovery.discover_experiments(scripts_dir)

        if human:
            table = Table(title="Available Experiments")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="green")
            table.add_column("Parameters", style="yellow")

            for exp in experiments:
                table.add_row(exp.name, exp.description, str(len(exp.parameters)))

            console.print(table)
        else:
            output = {
                "experiments": [
                    {
                        "name": exp.name,
                        "description": exp.description,
                        "parameter_count": len(exp.parameters),
                    }
                    for exp in experiments
                ]
            }
            print(json.dumps(output, indent=2))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@experiments_app.command("validate")
def experiments_validate(
    path: Path = typer.Argument(..., help="Path to Python script to validate"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Validate a Python script as a lab experiment.

    Checks if the script meets all requirements:
    - File exists and is a .py file
    - Contains a public function (no underscore prefix)
    - Function has return type annotation '-> dict'
    - Function has typed parameters
    - Parameters use Annotated for ranges (recommended)
    """
    from core import discovery

    try:
        result = discovery.validate_script(path)

        if human:
            # Header with validation result
            status_color = "green" if result["valid"] else "red"
            status_text = "VALID" if result["valid"] else "INVALID"
            console.print(
                f"\n[bold {status_color}]Validation Result: {status_text}[/bold {status_color}]"
            )
            console.print(f"[dim]File: {path}[/dim]\n")

            # Validation checks table
            table = Table(title="Validation Checks")
            table.add_column("Check", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Details", style="dim")

            for check in result["checks"]:
                status = (
                    "[green]✓ PASS[/green]" if check["passed"] else "[red]✗ FAIL[/red]"
                )
                table.add_row(check["check"], status, check["message"])

            console.print(table)

            # Errors
            if result["errors"]:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in result["errors"]:
                    console.print(f"  [red]•[/red] {error}")

            # Warnings
            if result["warnings"]:
                console.print("\n[bold yellow]Warnings:[/bold yellow]")
                for warning in result["warnings"]:
                    console.print(f"  [yellow]•[/yellow] {warning}")

            # Schema info if valid
            if result["valid"] and result["schema"]:
                schema = result["schema"]
                console.print(f"\n[bold cyan]Experiment Schema:[/bold cyan]")
                console.print(f"  Name: {schema['name']}")
                console.print(f"  Description: {schema['description'] or '(none)'}")
                console.print(f"  Module Path: {schema['module_path']}")

                if schema["parameters"]:
                    console.print("\n[bold cyan]Parameters:[/bold cyan]")
                    param_table = Table()
                    param_table.add_column("Name", style="cyan")
                    param_table.add_column("Type", style="green")
                    param_table.add_column("Required", style="yellow")
                    param_table.add_column("Default", style="magenta")
                    param_table.add_column("Range", style="blue")

                    for param in schema["parameters"]:
                        range_str = (
                            f"{param['range'][0]} to {param['range'][1]}"
                            if param["range"]
                            else "-"
                        )
                        param_table.add_row(
                            param["name"],
                            param["type"],
                            "Yes" if param["required"] else "No",
                            (
                                str(param["default"])
                                if param["default"] is not None
                                else "-"
                            ),
                            range_str,
                        )

                    console.print(param_table)

            console.print()
        else:
            print(json.dumps(result, indent=2))

        if not result["valid"]:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@experiments_app.command("schema")
def experiments_schema(
    name: str = typer.Argument(..., help="Experiment name"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Show schema for a specific experiment."""
    from core import discovery

    scripts_dir = get_scripts_dir()

    try:
        schema = discovery.get_experiment_schema(name, scripts_dir)

        if schema is None:
            console.print(f"[red]Experiment '{name}' not found[/red]")
            raise typer.Exit(1)

        if human:
            console.print(f"[bold cyan]Experiment:[/bold cyan] {schema.name}")
            console.print(f"[bold cyan]Description:[/bold cyan] {schema.description}")
            console.print()

            table = Table(title="Parameters")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Required", style="yellow")
            table.add_column("Default", style="magenta")
            table.add_column("Range", style="blue")

            for param in schema.parameters:
                table.add_row(
                    param.name,
                    param.type,
                    "Yes" if param.required else "No",
                    str(param.default) if param.default is not None else "-",
                    f"{param.range[0]} to {param.range[1]}" if param.range else "-",
                )

            console.print(table)
        else:
            print(json.dumps(schema.to_dict(), indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@experiments_app.command("run")
def experiments_run(
    name: str = typer.Argument(..., help="Experiment name"),
    params: str = typer.Option(..., "--params", "-p", help="Parameters as JSON string"),
    timeout: int = typer.Option(300, "--timeout", help="Timeout in seconds"),
    notes: str = typer.Option("", "--notes", help="User notes"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Run an experiment and store results."""
    from datetime import datetime, timezone
    from core import discovery, runner, storage
    from core.models import ExperimentResult

    scripts_dir = get_scripts_dir()
    data_dir = get_data_dir()

    try:
        # Parse params JSON
        try:
            params_dict = json.loads(params)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON in params:[/red] {e}")
            raise typer.Exit(1)

        if not isinstance(params_dict, dict):
            console.print("[red]Params must be a JSON object[/red]")
            raise typer.Exit(1)

        # Run experiment
        result_dict = runner.run_experiment(name, params_dict, scripts_dir, timeout)

        # Generate experiment ID
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat().replace("+00:00", "Z")
        exp_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{name}"

        target = params_dict.get("target")

        experiment_result = ExperimentResult(
            id=exp_id,
            type=name,
            timestamp=timestamp,
            status=result_dict["status"],
            target=target,
            params=params_dict,
            results=result_dict.get("results") or result_dict.get("data", {}),
            arrays=result_dict.get("arrays", {}),
            plots=result_dict.get("plots", []),
            notes=notes,
        )

        # Store results
        storage.save_experiment(experiment_result, data_dir)

        if human:
            console.print(
                f"[bold cyan]Experiment ID:[/bold cyan] {experiment_result.id}"
            )
            console.print(f"[bold cyan]Status:[/bold cyan] {experiment_result.status}")
            console.print(
                f"[bold cyan]Timestamp:[/bold cyan] {experiment_result.timestamp}"
            )
            if experiment_result.target:
                console.print(
                    f"[bold cyan]Target:[/bold cyan] {experiment_result.target}"
                )

            if experiment_result.results:
                console.print("[bold cyan]Results:[/bold cyan]")
                for key, value in experiment_result.results.items():
                    console.print(f"  {key}: {value}")

            if experiment_result.arrays:
                console.print(
                    f"[bold cyan]Arrays:[/bold cyan] {', '.join(experiment_result.arrays.keys())}"
                )

            if experiment_result.plots:
                console.print(
                    f"[bold cyan]Plots:[/bold cyan] {len(experiment_result.plots)}"
                )
        else:
            print(json.dumps(experiment_result.to_dict(), indent=2))

    except typer.Exit:
        raise
    except ValueError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(1)
    except TimeoutError as e:
        console.print(f"[red]Timeout:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# =============================================================================
# History Commands
# =============================================================================


@history_app.command("list")
def history_list(
    type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by experiment type"
    ),
    last: int = typer.Option(10, "--last", "-n", help="Limit to last N experiments"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """List past experiments."""
    from core import storage

    data_dir = get_data_dir()

    try:
        experiments = storage.search_experiments(data_dir, type=type, last=last)

        if human:
            if not experiments:
                console.print("[yellow]No experiments found[/yellow]")
                return

            table = Table(title=f"Experiment History (last {last})")
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Target", style="yellow")
            table.add_column("Timestamp", style="magenta")
            table.add_column("Status", style="blue")

            for exp in experiments:
                table.add_row(
                    exp["id"],
                    exp["type"],
                    exp.get("target", "-") or "-",
                    exp["timestamp"][:19],
                    exp["status"],
                )

            console.print(table)
        else:
            print(json.dumps({"experiments": experiments}, indent=2))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@history_app.command("show")
def history_show(
    id: str = typer.Argument(..., help="Experiment ID"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Show full metadata for a specific experiment."""
    from core import storage

    data_dir = get_data_dir()

    try:
        experiment = storage.load_experiment(id, data_dir)

        if experiment is None:
            console.print(f"[red]Experiment '{id}' not found[/red]")
            raise typer.Exit(1)

        if human:
            console.print(f"[bold cyan]ID:[/bold cyan] {experiment.id}")
            console.print(f"[bold cyan]Type:[/bold cyan] {experiment.type}")
            console.print(f"[bold cyan]Timestamp:[/bold cyan] {experiment.timestamp}")
            console.print(f"[bold cyan]Status:[/bold cyan] {experiment.status}")
            if experiment.target:
                console.print(f"[bold cyan]Target:[/bold cyan] {experiment.target}")
            if experiment.file_path:
                console.print(f"[bold cyan]File:[/bold cyan] {experiment.file_path}")

            if experiment.params:
                console.print("[bold cyan]Parameters:[/bold cyan]")
                for key, value in experiment.params.items():
                    console.print(f"  {key}: {value}")

            if experiment.results:
                console.print("[bold cyan]Results:[/bold cyan]")
                for key, value in experiment.results.items():
                    console.print(f"  {key}: {value}")

            if experiment.arrays:
                console.print(
                    f"[bold cyan]Arrays:[/bold cyan] {', '.join(experiment.arrays.keys())}"
                )

            if experiment.plots:
                console.print(
                    f"[bold cyan]Plots:[/bold cyan] {', '.join([p['name'] for p in experiment.plots])}"
                )

            if experiment.notes:
                console.print(f"[bold cyan]Notes:[/bold cyan] {experiment.notes}")
        else:
            print(json.dumps(experiment.to_dict(), indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@history_app.command("delete")
def history_delete(
    id: str = typer.Argument(..., help="Experiment ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete an experiment."""
    from core import storage

    data_dir = get_data_dir()

    try:
        experiment = storage.load_experiment(id, data_dir)
        if experiment is None:
            console.print(f"[red]Experiment '{id}' not found[/red]")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Delete experiment {id}?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        storage.delete_experiment(id, data_dir)
        console.print(f"[green]Deleted experiment:[/green] {id}")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@history_app.command("reindex")
def history_reindex():
    """Rebuild index from HDF5 files."""
    from core import storage

    data_dir = get_data_dir()

    try:
        storage.reindex(data_dir)
        experiments = storage.search_experiments(data_dir)
        console.print(f"[green]Reindexed {len(experiments)} experiments[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# =============================================================================
# Data Commands
# =============================================================================


@data_app.command("arrays")
def data_arrays(
    id: str = typer.Argument(..., help="Experiment ID"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """List all arrays in an experiment."""
    from core import storage

    data_dir = get_data_dir()

    try:
        arrays = storage.list_arrays(id, data_dir)

        if arrays is None:
            console.print(f"[red]Experiment '{id}' not found[/red]")
            raise typer.Exit(1)

        if human:
            if arrays:
                table = Table(title=f"Arrays in {id}")
                table.add_column("Name", style="cyan")
                table.add_column("Shape", style="green")
                table.add_column("Type", style="yellow")

                for arr in arrays:
                    table.add_row(arr["name"], str(arr["shape"]), arr["dtype"])

                console.print(table)
            else:
                console.print("[yellow]No arrays found[/yellow]")
        else:
            print(json.dumps({"arrays": arrays}, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@data_app.command("get")
def data_get(
    id: str = typer.Argument(..., help="Experiment ID"),
    array: str = typer.Argument(..., help="Array name"),
    slice_range: Optional[str] = typer.Option(
        None, "--slice", "-s", help="Slice range (START:END)"
    ),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Get array data (full or sliced)."""
    from core import storage

    data_dir = get_data_dir()

    try:
        start_idx = None
        end_idx = None
        if slice_range:
            parts = slice_range.split(":")
            if len(parts) != 2:
                console.print("[red]Slice must be in format START:END[/red]")
                raise typer.Exit(1)
            start_idx = int(parts[0]) if parts[0] else None
            end_idx = int(parts[1]) if parts[1] else None

        data = storage.get_array(id, array, data_dir, start=start_idx, end=end_idx)

        if data is None:
            console.print(f"[red]Array '{array}' not found in '{id}'[/red]")
            raise typer.Exit(1)

        # Convert to list for JSON
        if hasattr(data, "tolist"):
            data = data.tolist()

        if human:
            console.print(f"[bold cyan]Array:[/bold cyan] {array}")
            console.print(
                f"[bold cyan]Length:[/bold cyan] {len(data) if isinstance(data, list) else 'N/A'}"
            )
            console.print(f"[bold cyan]Data:[/bold cyan]")
            console.print(str(data))
        else:
            print(json.dumps({"array": array, "data": data}, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@data_app.command("stats")
def data_stats(
    id: str = typer.Argument(..., help="Experiment ID"),
    array: str = typer.Argument(..., help="Array name"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Get array statistics (min, max, mean, std)."""
    from core import storage

    data_dir = get_data_dir()

    try:
        stats = storage.get_array_stats(id, array, data_dir)

        if stats is None:
            console.print(f"[red]Array '{array}' not found in '{id}'[/red]")
            raise typer.Exit(1)

        if human:
            console.print(f"[bold cyan]Array:[/bold cyan] {array}")
            console.print(f"[bold cyan]Min:[/bold cyan] {stats['min']}")
            console.print(f"[bold cyan]Max:[/bold cyan] {stats['max']}")
            console.print(f"[bold cyan]Mean:[/bold cyan] {stats['mean']}")
            console.print(f"[bold cyan]Std:[/bold cyan] {stats['std']}")
            console.print(f"[bold cyan]Count:[/bold cyan] {stats['count']}")
        else:
            print(json.dumps({"array": array, "stats": stats}, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@data_app.command("plots")
def data_plots(
    id: str = typer.Argument(..., help="Experiment ID"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """List all plots in an experiment."""
    from core import storage

    data_dir = get_data_dir()

    try:
        plots = storage.list_plots(id, data_dir)

        if plots is None:
            console.print(f"[red]Experiment '{id}' not found[/red]")
            raise typer.Exit(1)

        if human:
            if plots:
                table = Table(title=f"Plots in {id}")
                table.add_column("Name", style="cyan")
                table.add_column("Format", style="green")

                for plot in plots:
                    table.add_row(plot["name"], plot["format"])

                console.print(table)
            else:
                console.print("[yellow]No plots found[/yellow]")
        else:
            print(json.dumps({"plots": plots}, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@data_app.command("plot")
def data_plot(
    id: str = typer.Argument(..., help="Experiment ID"),
    name: str = typer.Argument(..., help="Plot name"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
):
    """Extract a plot (PNG or Plotly JSON)."""
    import base64
    from core import storage

    data_dir = get_data_dir()

    try:
        plot_data = storage.get_plot(id, name, data_dir)

        if plot_data is None:
            console.print(f"[red]Plot '{name}' not found in '{id}'[/red]")
            raise typer.Exit(1)

        if output:
            if plot_data["format"] == "png":
                with open(output, "wb") as f:
                    f.write(base64.b64decode(plot_data["data"]))
            else:
                with open(output, "w") as f:
                    if isinstance(plot_data["data"], dict):
                        json.dump(plot_data["data"], f, indent=2)
                    else:
                        f.write(plot_data["data"])

            console.print(f"[green]Saved plot to:[/green] {output}")
        else:
            console.print(f"[bold cyan]Plot:[/bold cyan] {name}")
            console.print(f"[bold cyan]Format:[/bold cyan] {plot_data['format']}")
            if plot_data["format"] == "png":
                console.print("[yellow]Use --output to save PNG file[/yellow]")
            else:
                print(json.dumps(plot_data, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# =============================================================================
# Workflow Commands
# =============================================================================


def get_workflows_dir() -> Path:
    """Get workflows directory path."""
    return get_data_dir() / "workflows"


def load_workflow(workflow_id: str) -> Optional[dict]:
    """Load workflow.json for a given workflow ID."""
    workflow_path = get_workflows_dir() / workflow_id / "workflow.json"
    if not workflow_path.exists():
        return None
    with open(workflow_path) as f:
        return json.load(f)


def load_workflow_history(workflow_id: str) -> list:
    """Load history.jsonl for a given workflow ID."""
    history_path = get_workflows_dir() / workflow_id / "history.jsonl"
    if not history_path.exists():
        return []
    events = []
    with open(history_path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def list_all_workflows() -> list:
    """List all workflows with basic info."""
    workflows_dir = get_workflows_dir()
    if not workflows_dir.exists():
        return []

    workflows = []
    for entry in workflows_dir.iterdir():
        if entry.is_dir():
            workflow = load_workflow(entry.name)
            if workflow:
                workflows.append(
                    {
                        "id": workflow.get("id", entry.name),
                        "name": workflow.get("name", ""),
                        "status": workflow.get("status", "unknown"),
                        "created": workflow.get("created", ""),
                        "node_count": len(workflow.get("nodes", [])),
                    }
                )

    # Sort by created date (newest first)
    workflows.sort(key=lambda w: w.get("created", ""), reverse=True)
    return workflows


def count_node_states(workflow: dict) -> dict:
    """Count nodes in each state."""
    counts = {"pending": 0, "running": 0, "success": 0, "failed": 0, "skipped": 0}
    for node in workflow.get("nodes", []):
        state = node.get("state", "pending")
        if state in counts:
            counts[state] += 1
    return counts


def validate_workflow_structure(workflow: dict) -> list:
    """Validate workflow structure and return list of issues."""
    issues = []

    # Check required fields
    if "id" not in workflow:
        issues.append("Missing required field: id")
    if "nodes" not in workflow:
        issues.append("Missing required field: nodes")
        return issues

    nodes = workflow.get("nodes", [])
    node_ids = {node.get("id") for node in nodes}

    # Check each node
    for i, node in enumerate(nodes):
        node_id = node.get("id", f"node_{i}")

        if "id" not in node:
            issues.append(f"Node {i}: Missing 'id' field")

        if "experiment" not in node and "name" not in node:
            issues.append(f"Node '{node_id}': Missing 'experiment' or 'name' field")

        # Check dependencies exist
        for dep in node.get("dependencies", []):
            if dep not in node_ids:
                issues.append(f"Node '{node_id}': Dependency '{dep}' not found")

    # Check for cycles (simple DFS)
    def has_cycle(node_id, visited, stack):
        visited.add(node_id)
        stack.add(node_id)

        node = next((n for n in nodes if n.get("id") == node_id), None)
        if node:
            for dep in node.get("dependencies", []):
                if dep not in visited:
                    if has_cycle(dep, visited, stack):
                        return True
                elif dep in stack:
                    return True

        stack.remove(node_id)
        return False

    visited = set()
    for node in nodes:
        node_id = node.get("id")
        if node_id and node_id not in visited:
            if has_cycle(node_id, visited, set()):
                issues.append("Circular dependency detected in workflow graph")
                break

    return issues


@workflow_app.command("list")
def workflow_list(
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """List all workflows with status."""
    try:
        workflows = list_all_workflows()

        if human:
            if not workflows:
                console.print("[yellow]No workflows found[/yellow]")
                return

            table = Table(title="Workflows")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Nodes", style="blue")
            table.add_column("Created", style="dim")

            for wf in workflows:
                status_style = {
                    "running": "[bold green]running[/bold green]",
                    "completed": "[green]completed[/green]",
                    "failed": "[red]failed[/red]",
                    "paused": "[yellow]paused[/yellow]",
                    "created": "[dim]created[/dim]",
                }.get(wf["status"], wf["status"])

                table.add_row(
                    wf["id"],
                    wf["name"],
                    status_style,
                    str(wf["node_count"]),
                    wf["created"][:10] if wf["created"] else "-",
                )

            console.print(table)
        else:
            print(json.dumps({"workflows": workflows}, indent=2))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workflow_app.command("show")
def workflow_show(
    id: str = typer.Argument(..., help="Workflow ID"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Show full workflow definition."""
    try:
        workflow = load_workflow(id)

        if workflow is None:
            console.print(f"[red]Workflow '{id}' not found[/red]")
            raise typer.Exit(1)

        if human:
            console.print(f"[bold cyan]ID:[/bold cyan] {workflow.get('id', id)}")
            console.print(f"[bold cyan]Name:[/bold cyan] {workflow.get('name', '-')}")
            console.print(
                f"[bold cyan]Description:[/bold cyan] {workflow.get('description', '-')}"
            )
            console.print(
                f"[bold cyan]Status:[/bold cyan] {workflow.get('status', 'unknown')}"
            )
            console.print(
                f"[bold cyan]Created:[/bold cyan] {workflow.get('created', '-')}"
            )
            console.print()

            # Show nodes summary
            nodes = workflow.get("nodes", [])
            counts = count_node_states(workflow)
            console.print(f"[bold cyan]Nodes:[/bold cyan] {len(nodes)} total")
            console.print(
                f"  Success: {counts['success']}, Failed: {counts['failed']}, "
                f"Running: {counts['running']}, Pending: {counts['pending']}, "
                f"Skipped: {counts['skipped']}"
            )
            console.print()

            if workflow.get("global_params"):
                console.print("[bold cyan]Global Parameters:[/bold cyan]")
                for key, value in workflow["global_params"].items():
                    console.print(f"  {key}: {value}")
                console.print()

            if workflow.get("completion_criteria"):
                console.print("[bold cyan]Completion Criteria:[/bold cyan]")
                for key, value in workflow["completion_criteria"].items():
                    console.print(f"  {key}: {value}")
        else:
            print(json.dumps(workflow, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workflow_app.command("status")
def workflow_status(
    id: str = typer.Argument(..., help="Workflow ID"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Show runtime status and progress."""
    try:
        workflow = load_workflow(id)

        if workflow is None:
            console.print(f"[red]Workflow '{id}' not found[/red]")
            raise typer.Exit(1)

        nodes = workflow.get("nodes", [])
        counts = count_node_states(workflow)
        total = len(nodes)
        completed = counts["success"] + counts["failed"] + counts["skipped"]
        progress = (completed / total * 100) if total > 0 else 0

        # Find current node
        current_node = None
        for node in nodes:
            if node.get("state") == "running":
                current_node = node
                break

        # Find next pending node
        next_node = None
        completed_ids = {
            n.get("id") for n in nodes if n.get("state") in ("success", "skipped")
        }
        for node in nodes:
            if node.get("state") == "pending":
                deps = set(node.get("dependencies", []))
                if deps.issubset(completed_ids):
                    next_node = node
                    break

        status_info = {
            "id": workflow.get("id", id),
            "status": workflow.get("status", "unknown"),
            "progress": round(progress, 1),
            "nodes_completed": completed,
            "nodes_total": total,
            "current_node": current_node.get("id") if current_node else None,
            "current_node_name": current_node.get("name") if current_node else None,
            "next_node": next_node.get("id") if next_node else None,
            "started_at": workflow.get("started_at"),
            "paused_at": workflow.get("paused_at"),
            "paused_reason": workflow.get("paused_reason"),
            "suggestions": workflow.get("suggestions", []),
        }

        if human:
            console.print(f"[bold cyan]Workflow:[/bold cyan] {status_info['id']}")

            status_display = {
                "running": "[bold green]● RUNNING[/bold green]",
                "completed": "[green]✓ COMPLETED[/green]",
                "failed": "[red]✗ FAILED[/red]",
                "paused": "[yellow]⏸ PAUSED[/yellow]",
                "created": "[dim]○ CREATED[/dim]",
            }.get(status_info["status"], status_info["status"])
            console.print(f"[bold cyan]Status:[/bold cyan] {status_display}")

            # Progress bar
            bar_width = 30
            filled = int(progress / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            console.print(
                f"[bold cyan]Progress:[/bold cyan] [{bar}] {progress:.1f}% ({completed}/{total} nodes)"
            )
            console.print()

            if current_node:
                console.print(
                    f"[bold cyan]Current Node:[/bold cyan] {current_node.get('name', current_node.get('id'))}"
                )
                if current_node.get("started_at"):
                    console.print(f"  Started: {current_node['started_at']}")
                if current_node.get("run_count", 0) > 1:
                    console.print(f"  Attempt: {current_node['run_count']}")
                console.print()

            if next_node and status_info["status"] != "running":
                console.print(
                    f"[bold cyan]Next Node:[/bold cyan] {next_node.get('name', next_node.get('id'))}"
                )
                console.print()

            if status_info["paused_reason"]:
                console.print(
                    f"[yellow]Paused Reason:[/yellow] {status_info['paused_reason']}"
                )
                console.print()

            if status_info["suggestions"]:
                console.print("[bold cyan]Suggestions:[/bold cyan]")
                for i, sug in enumerate(status_info["suggestions"], 1):
                    if isinstance(sug, dict):
                        console.print(
                            f"  {i}. {sug.get('action', 'unknown')}: {sug.get('reason', '')}"
                        )
                    else:
                        console.print(f"  {i}. {sug}")
        else:
            print(json.dumps(status_info, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workflow_app.command("validate")
def workflow_validate(
    id: str = typer.Argument(..., help="Workflow ID"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Validate workflow structure and DAG."""
    try:
        workflow = load_workflow(id)

        if workflow is None:
            console.print(f"[red]Workflow '{id}' not found[/red]")
            raise typer.Exit(1)

        issues = validate_workflow_structure(workflow)
        valid = len(issues) == 0

        if human:
            if valid:
                console.print(f"[bold green]✓ Workflow '{id}' is valid[/bold green]")
            else:
                console.print(
                    f"[bold red]✗ Workflow '{id}' has {len(issues)} issue(s):[/bold red]"
                )
                for issue in issues:
                    console.print(f"  • {issue}")
        else:
            print(json.dumps({"id": id, "valid": valid, "issues": issues}, indent=2))

        if not valid:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workflow_app.command("history")
def workflow_history(
    id: str = typer.Argument(..., help="Workflow ID"),
    last: Optional[int] = typer.Option(None, "--last", "-n", help="Show last N events"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """Show workflow execution history."""
    try:
        workflow = load_workflow(id)
        if workflow is None:
            console.print(f"[red]Workflow '{id}' not found[/red]")
            raise typer.Exit(1)

        events = load_workflow_history(id)

        if last:
            events = events[-last:]

        if human:
            if not events:
                console.print("[yellow]No history events found[/yellow]")
                return

            table = Table(title=f"History for {id}")
            table.add_column("Timestamp", style="dim")
            table.add_column("Event", style="cyan")
            table.add_column("Node", style="green")
            table.add_column("Details", style="yellow")

            for event in events:
                ts = event.get("ts", "")[:19]
                event_type = event.get("event", "unknown")
                node = event.get("node", "-")

                details_parts = []
                if "run" in event:
                    details_parts.append(f"run={event['run']}")
                if "result" in event:
                    details_parts.append(f"result={event['result']}")
                if "attempts" in event:
                    details_parts.append(f"attempts={event['attempts']}")
                if "state" in event:
                    details_parts.append(f"state={event['state']}")
                if "reason" in event:
                    reason = (
                        event["reason"][:30] + "..."
                        if len(event.get("reason", "")) > 30
                        else event.get("reason", "")
                    )
                    details_parts.append(f"reason={reason}")
                details = ", ".join(details_parts) if details_parts else "-"

                table.add_row(ts, event_type, node, details)

            console.print(table)
        else:
            print(json.dumps({"events": events}, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workflow_app.command("nodes")
def workflow_nodes(
    id: str = typer.Argument(..., help="Workflow ID"),
    human: bool = typer.Option(False, "--human", "-h", help="Human-readable output"),
):
    """List all nodes with state and dependencies."""
    try:
        workflow = load_workflow(id)

        if workflow is None:
            console.print(f"[red]Workflow '{id}' not found[/red]")
            raise typer.Exit(1)

        nodes = workflow.get("nodes", [])

        if human:
            if not nodes:
                console.print("[yellow]No nodes in this workflow[/yellow]")
                return

            table = Table(title=f"Nodes in {id}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("State", style="yellow")
            table.add_column("Dependencies", style="magenta")
            table.add_column("Experiment", style="blue")
            table.add_column("Runs", style="dim")

            for node in nodes:
                state = node.get("state", "pending")
                state_display = {
                    "pending": "[dim]pending[/dim]",
                    "running": "[bold yellow]running[/bold yellow]",
                    "success": "[green]success[/green]",
                    "failed": "[red]failed[/red]",
                    "skipped": "[dim]skipped[/dim]",
                }.get(state, state)

                deps = ", ".join(node.get("dependencies", [])) or "-"
                experiment = node.get("experiment", "-")
                runs = str(node.get("run_count", 0))

                table.add_row(
                    node.get("id", "-"),
                    node.get("name", "-"),
                    state_display,
                    deps,
                    experiment,
                    runs,
                )

            console.print(table)

            # Show extracted values if any
            extracted_nodes = [n for n in nodes if n.get("extracted")]
            if extracted_nodes:
                console.print()
                console.print("[bold cyan]Extracted Values:[/bold cyan]")
                for node in extracted_nodes:
                    console.print(f"  {node.get('id')}:")
                    for key, value in node.get("extracted", {}).items():
                        console.print(f"    {key}: {value}")
        else:
            print(json.dumps({"nodes": nodes}, indent=2))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workflow_app.command("watch")
def workflow_watch(
    id: str = typer.Argument(..., help="Workflow ID"),
    interval: float = typer.Option(
        2.0, "--interval", "-i", help="Poll interval in seconds"
    ),
):
    """Live-watch workflow progress (polls status)."""
    from datetime import datetime

    try:
        # Initial check
        workflow = load_workflow(id)
        if workflow is None:
            console.print(f"[red]Workflow '{id}' not found[/red]")
            raise typer.Exit(1)

        console.print(f"[bold cyan]Watching workflow:[/bold cyan] {id}")
        console.print(f"[dim]Press Ctrl+C to stop[/dim]")
        console.print()

        last_events_count = 0

        with Live(console=console, refresh_per_second=1) as live:
            while True:
                workflow = load_workflow(id)
                if workflow is None:
                    live.update("[red]Workflow not found[/red]")
                    break

                nodes = workflow.get("nodes", [])
                counts = count_node_states(workflow)
                total = len(nodes)
                completed = counts["success"] + counts["failed"] + counts["skipped"]
                progress = (completed / total * 100) if total > 0 else 0

                # Find current node
                current_node = None
                for node in nodes:
                    if node.get("state") == "running":
                        current_node = node
                        break

                # Build display
                lines = []

                status = workflow.get("status", "unknown")
                status_display = {
                    "running": "[bold green]● RUNNING[/bold green]",
                    "completed": "[green]✓ COMPLETED[/green]",
                    "failed": "[red]✗ FAILED[/red]",
                    "paused": "[yellow]⏸ PAUSED[/yellow]",
                    "created": "[dim]○ CREATED[/dim]",
                }.get(status, status)
                lines.append(f"Status: {status_display}")

                # Progress bar
                bar_width = 40
                filled = int(progress / 100 * bar_width)
                bar = "█" * filled + "░" * (bar_width - filled)
                lines.append(f"Progress: [{bar}] {progress:.1f}%")
                lines.append(
                    f"Nodes: {counts['success']} ✓  {counts['failed']} ✗  {counts['running']} ●  {counts['pending']} ○  {counts['skipped']} ○"
                )

                if current_node:
                    lines.append(
                        f"Current: {current_node.get('name', current_node.get('id'))}"
                    )
                    if current_node.get("run_count", 0) > 1:
                        lines.append(f"         Attempt {current_node['run_count']}")

                if workflow.get("paused_reason"):
                    lines.append(
                        f"[yellow]Paused: {workflow['paused_reason']}[/yellow]"
                    )

                # Check for new history events
                events = load_workflow_history(id)
                if len(events) > last_events_count:
                    new_events = events[last_events_count:]
                    last_events_count = len(events)
                    for event in new_events[-3:]:
                        event_type = event.get("event", "unknown")
                        node_id = event.get("node", "")
                        lines.append(f"[dim]→ {event_type} {node_id}[/dim]")

                lines.append("")
                lines.append(
                    f"[dim]Last updated: {datetime.now().strftime('%H:%M:%S')}[/dim]"
                )

                live.update("\n".join(lines))

                # Exit if workflow is done
                if status in ("completed", "failed"):
                    console.print()
                    console.print(f"[bold]Workflow {status}[/bold]")
                    break

                time.sleep(interval)

    except KeyboardInterrupt:
        console.print()
        console.print("[dim]Stopped watching[/dim]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# =============================================================================
# Serve Command
# =============================================================================


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for development"
    ),
    workers: int = typer.Option(
        1, "--workers", "-w", help="Number of worker processes"
    ),
):
    """Launch the QCA backend server.

    Examples:
        qca serve                        # Start on 0.0.0.0:8000
        qca serve -p 9000                # Custom port
        qca serve --reload               # Dev mode with auto-reload
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Run: pip install uvicorn[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Starting QCA server on {host}:{port}[/green]")
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
    )


# =============================================================================
# Entry Point
# =============================================================================


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
