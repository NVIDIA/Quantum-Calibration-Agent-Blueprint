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

"""QCA Server - FastAPI server with Deep Agent integration.

Single server that handles:
- Chat streaming via Deep Agent
- Knowledge API (markdown files)
- History API (experiment results from HDF5/SQLite)
- Experiment/Apparatus API (script discovery via AST)
"""

import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend

from core import storage, discovery
from prompt import load_system_prompt

# Load environment
load_dotenv()

# =============================================================================
# Directory Configuration
# =============================================================================

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "cookbook" / "data" / "experiments"  # Where index.db and HDF5 files are
KNOWLEDGE_DIR = ROOT_DIR / "cookbook" / "data" / "knowledge"
SCRIPTS_DIR = ROOT_DIR / "scripts"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
KNOWLEDGE_DIR.mkdir(exist_ok=True)
SCRIPTS_DIR.mkdir(exist_ok=True)

# =============================================================================
# Agent Runtime
# =============================================================================

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


def load_tools() -> list:
    """Load tools for the agent."""
    tools = []

    # Try to load lab tools
    try:
        sys.path.insert(0, str(ROOT_DIR / "tools"))
        from lab_tool import lab, run_experiment

        tools.extend([lab, run_experiment])
    except ImportError:
        pass

    # Try to load workflow tool
    try:
        from workflow_tool import workflow

        tools.append(workflow)
    except ImportError:
        pass

    # Try to load VLM inspection tool
    try:
        from vlm_tool import vlm_inspect

        tools.append(vlm_inspect)
    except ImportError:
        pass

    return tools


def create_agent():
    """Create the Deep Agent."""
    backend = LocalShellBackend(
        root_dir=str(ROOT_DIR),
        virtual_mode=True,  # Restrict file access to within project directory
        inherit_env=True,
    )

    system_prompt = load_system_prompt()
    tools = load_tools()
    checkpointer = MemorySaver()

    # Tools requiring user approval before execution
    # HITL disabled - uncomment to re-enable approval prompts
    # interrupt_on = {
    #     "run_experiment": True,
    #     "write_file": True,
    #     "execute": True,
    # }
    interrupt_on = {}

    chat_model = create_chat_model(DEFAULT_MODEL)

    agent = create_deep_agent(
        model=chat_model,
        backend=backend,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        interrupt_on=interrupt_on,
    )

    return agent, backend, checkpointer


# Global agent instance
_agent = None
_backend = None
_checkpointer = None

# In-memory storage for pending interrupts (thread_id -> interrupt data)
pending_interrupts: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent on startup."""
    global _agent, _backend, _checkpointer
    print("QCA Server starting...")
    _agent, _backend, _checkpointer = create_agent()
    print(f"Agent initialized with model: {DEFAULT_MODEL}")
    yield
    print("QCA Server shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(title="QCA Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # explicit allowed origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# =============================================================================
# Chat Models
# =============================================================================


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    thread_id: Optional[str] = None


class ResumeRequest(BaseModel):
    thread_id: str
    decisions: list[
        dict
    ]  # [{"type": "approve"} | {"type": "reject", "message": "..."}]


def convert_to_langchain_messages(messages: list[dict]) -> list:
    """Convert chat messages to LangChain format."""
    result = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        elif role == "system":
            result.append(SystemMessage(content=content))
    return result


# =============================================================================
# Tool Formatting
# =============================================================================

TOOL_ICONS = {
    "ls": "📂",
    "read_file": "📄",
    "write_file": "✏️",
    "edit_file": "✏️",
    "execute": "💻",
    "glob": "🔍",
    "grep": "🔎",
    "task": "🤖",
    "lab": "🔬",
    "run_experiment": "⚛️",
    "workflow": "📋",
}


def format_tool_call(tool_name: str, tool_args: dict) -> tuple[str, str]:
    """Format tool call for display."""
    icon = TOOL_ICONS.get(tool_name, "🔧")
    name = f"{icon} {tool_name}"
    payload = json.dumps(tool_args, indent=2) if tool_args else ""
    return name, payload


def format_tool_result(tool_name: str, result: str) -> tuple[str, str]:
    """Format tool result for display."""
    icon = TOOL_ICONS.get(tool_name, "🔧")
    name = f"{icon} {tool_name} Result"

    # Wrap JSON in code block for proper rendering
    result_stripped = result.strip()
    if result_stripped.startswith("{") and result_stripped.endswith("}"):
        try:
            parsed = json.loads(result_stripped)
            result = f"```json\n{json.dumps(parsed, indent=2)}\n```"
        except json.JSONDecodeError:
            pass

    return name, result


def _build_interrupt_messages(
    *,
    thread_id: str,
    interrupt_id: str | None,
    actions: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build both UI interaction message and legacy interrupt payloads."""
    action_descriptions = []
    for action in actions:
        name = action.get("name", "unknown")
        args = action.get("args", {})
        icon = TOOL_ICONS.get(name, "🔧")

        # Format action with icon and args in code block
        action_text = f"### {icon} {name}\n\n"
        if args:
            action_text += f"```json\n{json.dumps(args, indent=2)}\n```"
        action_descriptions.append(action_text)

    interaction_text = "## Approve the following action?\n\n" + "\n\n".join(
        action_descriptions
    )

    # NAT UI format (system_interaction_message)
    interaction_message = {
        "type": "system_interaction_message",
        "id": interrupt_id or f"interrupt_{uuid.uuid4().hex[:8]}",
        "thread_id": thread_id,
        "content": {
            "input_type": "binary_choice",
            "text": interaction_text,
            "options": [
                {"id": "approve", "label": "Approve", "value": "approve"},
                {"id": "reject", "label": "Reject", "value": "reject"},
            ],
            "timeout": 300,
        },
    }

    # Legacy format for proxy compatibility
    legacy_interrupt = {
        "interrupt_id": interrupt_id,
        "thread_id": thread_id,
        "actions": actions,
    }

    return interaction_message, legacy_interrupt


# =============================================================================
# Chat Endpoints
# =============================================================================


@app.get("/health")
async def health():
    return {"status": "ok", "agent": _agent is not None}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint with intermediate steps."""
    messages = convert_to_langchain_messages([m.model_dump() for m in request.messages])
    thread_id = request.thread_id or f"thread_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}

    async def event_stream():
        step_counter = 0
        last_tool_name = "unknown"
        pending_tool_ids: dict[str, str] = {}

        # Send thread_id
        yield f"thread_id: {thread_id}\n\n"

        try:
            async for chunk in _agent.astream(
                {"messages": messages},
                config=config,
                stream_mode=["messages", "updates"],
                subgraphs=True,
            ):
                if isinstance(chunk, tuple) and len(chunk) == 3:
                    namespace, mode, data = chunk
                    if namespace != ():
                        continue

                    # Handle updates (interrupts and tool results)
                    if mode == "updates" and isinstance(data, dict):
                        # Check for interrupt (permission request)
                        if "__interrupt__" in data:
                            interrupts = data["__interrupt__"]
                            if interrupts:
                                for interrupt_obj in interrupts:
                                    interrupt_value = (
                                        getattr(interrupt_obj, "value", {})
                                        if hasattr(interrupt_obj, "value")
                                        else interrupt_obj
                                    )
                                    interrupt_id = getattr(interrupt_obj, "id", None)

                                    # Extract action requests
                                    actions = []
                                    if isinstance(interrupt_value, dict):
                                        action_requests = interrupt_value.get(
                                            "action_requests", []
                                        )
                                        for action in action_requests:
                                            actions.append(
                                                {
                                                    "name": action.get(
                                                        "name", "unknown"
                                                    ),
                                                    "args": action.get("args", {}),
                                                    "description": action.get(
                                                        "description", ""
                                                    ),
                                                }
                                            )

                                    # Show awaiting approval in intermediate steps
                                    awaiting_step_ids = []
                                    for tool_id, step_id in pending_tool_ids.items():
                                        awaiting_step_ids.append(step_id)
                                        intermediate = {
                                            "type": "system_intermediate",
                                            "id": step_id,
                                            "name": "⏳ Awaiting Approval",
                                            "payload": "Tool requires human approval before execution",
                                            "status": "in_progress",
                                        }
                                        yield f"intermediate_data: {json.dumps(intermediate)}\n\n"
                                    pending_tool_ids.clear()

                                    # Store pending interrupt
                                    pending_interrupts[thread_id] = {
                                        "interrupt_id": interrupt_id,
                                        "interrupt_value": interrupt_value,
                                        "actions": actions,
                                        "awaiting_step_ids": awaiting_step_ids,
                                        "step_counter": step_counter,  # Preserve step numbering
                                    }

                                    # Build and send interrupt messages
                                    interaction_message, legacy_interrupt = (
                                        _build_interrupt_messages(
                                            thread_id=thread_id,
                                            interrupt_id=interrupt_id,
                                            actions=actions,
                                        )
                                    )
                                    yield f"data: {json.dumps(interaction_message)}\n\n"
                                    yield f"interrupt: {json.dumps(legacy_interrupt)}\n\n"
                                    return  # Stop streaming, wait for user decision

                        # Handle tool results
                        for key, value in data.items():
                            if (
                                key == "tools"
                                and isinstance(value, dict)
                                and "messages" in value
                            ):
                                msg_list = value["messages"]
                                if hasattr(msg_list, "value"):
                                    msg_list = msg_list.value
                                if isinstance(msg_list, list):
                                    for msg in msg_list:
                                        if isinstance(msg, ToolMessage):
                                            tool_content = str(msg.content)
                                            tool_name = getattr(
                                                msg, "name", last_tool_name
                                            )
                                            tool_call_id = getattr(
                                                msg, "tool_call_id", None
                                            )
                                            step_id = pending_tool_ids.pop(
                                                tool_call_id, None
                                            )
                                            if not step_id:
                                                step_counter += 1
                                                step_id = f"step_{step_counter}"
                                            name, payload = format_tool_result(
                                                tool_name, tool_content
                                            )
                                            intermediate = {
                                                "type": "system_intermediate",
                                                "id": step_id,
                                                "name": name,
                                                "payload": payload,
                                                "status": "complete",
                                            }
                                            yield f"intermediate_data: {json.dumps(intermediate)}\n\n"

                    # Handle messages (token streaming)
                    elif (
                        mode == "messages"
                        and isinstance(data, tuple)
                        and len(data) == 2
                    ):
                        message, metadata = data

                        # Skip ToolMessage content - we show these via intermediate_data
                        # Emit newline to maintain separation between pre/post tool text
                        if isinstance(message, ToolMessage):
                            newline_chunk = {
                                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                "object": "chat.completion.chunk",
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": "\n\n"},
                                        "finish_reason": None,
                                    }
                                ],
                            }
                            yield f"data: {json.dumps(newline_chunk)}\n\n"
                            continue

                        content_blocks = []
                        if (
                            hasattr(message, "content_blocks")
                            and message.content_blocks
                        ):
                            content_blocks = message.content_blocks
                        elif hasattr(message, "content") and isinstance(
                            message.content, list
                        ):
                            content_blocks = message.content

                        for block in content_blocks:
                            if isinstance(block, dict):
                                block_type = block.get("type", "text")

                                # Stream text
                                if block_type == "text" or "text" in block:
                                    text = block.get("text", "")
                                    if text:
                                        chunk_data = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                            "object": "chat.completion.chunk",
                                            "choices": [
                                                {
                                                    "index": 0,
                                                    "delta": {"content": text},
                                                    "finish_reason": None,
                                                }
                                            ],
                                        }
                                        yield f"data: {json.dumps(chunk_data)}\n\n"

                                # Handle tool calls
                                elif block_type in ("tool_call", "tool_use"):
                                    tool_name = block.get("name", "unknown")
                                    tool_args = block.get("args", {})
                                    tool_id = block.get("id")
                                    last_tool_name = tool_name

                                    step_counter += 1
                                    step_id = f"step_{step_counter}"
                                    if tool_id:
                                        pending_tool_ids[tool_id] = step_id

                                    name, payload = format_tool_call(
                                        tool_name, tool_args
                                    )
                                    intermediate = {
                                        "type": "system_intermediate",
                                        "id": step_id,
                                        "name": name,
                                        "payload": payload,
                                        "status": "in_progress",
                                    }
                                    yield f"intermediate_data: {json.dumps(intermediate)}\n\n"

            # Final chunk
            yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat/resume")
async def chat_resume(request: ResumeRequest):
    """Resume an interrupted conversation with user's decision."""
    thread_id = request.thread_id
    decisions = request.decisions

    if thread_id not in pending_interrupts:
        return {"error": f"No pending interrupt for thread {thread_id}"}

    # Get pending interrupt data
    interrupt_info = pending_interrupts.pop(thread_id)
    interrupt_id = interrupt_info.get("interrupt_id")
    awaiting_step_ids = interrupt_info.get("awaiting_step_ids", [])

    # Convert decisions to LangGraph format
    lg_decisions = []
    for decision in decisions:
        if decision.get("type") == "approve":
            lg_decisions.append({"type": "approve"})
        elif decision.get("type") == "reject":
            lg_decisions.append(
                {
                    "type": "reject",
                    "message": decision.get("message", "User rejected the action"),
                }
            )

    # Build resume payload for LangGraph
    if interrupt_id:
        resume_payload = {interrupt_id: {"decisions": lg_decisions}}
    else:
        resume_payload = {"decisions": lg_decisions}

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}

    async def resume_stream():
        # Continue step numbering from where the initial chat left off
        step_counter = interrupt_info.get("step_counter", len(awaiting_step_ids))
        last_tool_name = "unknown"
        pending_tool_ids: dict[str, str] = {}

        # Send thread_id first
        yield f"thread_id: {thread_id}\n\n"

        try:
            async for chunk in _agent.astream(
                Command(resume=resume_payload),
                config=config,
                stream_mode=["messages", "updates"],
                subgraphs=True,
            ):
                if isinstance(chunk, tuple) and len(chunk) == 3:
                    namespace, mode, data = chunk
                    if namespace != ():
                        continue

                    # Handle updates (interrupts and tool results)
                    if mode == "updates" and isinstance(data, dict):
                        # Check for another interrupt
                        if "__interrupt__" in data:
                            interrupts = data["__interrupt__"]
                            if interrupts:
                                for interrupt_obj in interrupts:
                                    interrupt_value = (
                                        getattr(interrupt_obj, "value", {})
                                        if hasattr(interrupt_obj, "value")
                                        else interrupt_obj
                                    )
                                    new_interrupt_id = getattr(
                                        interrupt_obj, "id", None
                                    )

                                    actions = []
                                    if isinstance(interrupt_value, dict):
                                        for action in interrupt_value.get(
                                            "action_requests", []
                                        ):
                                            actions.append(
                                                {
                                                    "name": action.get(
                                                        "name", "unknown"
                                                    ),
                                                    "args": action.get("args", {}),
                                                    "description": action.get(
                                                        "description", ""
                                                    ),
                                                }
                                            )

                                    # Store new pending interrupt
                                    pending_interrupts[thread_id] = {
                                        "interrupt_id": new_interrupt_id,
                                        "interrupt_value": interrupt_value,
                                        "actions": actions,
                                        "awaiting_step_ids": [],
                                        "step_counter": step_counter,  # Preserve step numbering
                                    }

                                    interaction_message, legacy_interrupt = (
                                        _build_interrupt_messages(
                                            thread_id=thread_id,
                                            interrupt_id=new_interrupt_id,
                                            actions=actions,
                                        )
                                    )
                                    yield f"data: {json.dumps(interaction_message)}\n\n"
                                    yield f"interrupt: {json.dumps(legacy_interrupt)}\n\n"
                                    return

                        # Handle tool results
                        for key, value in data.items():
                            if (
                                key == "tools"
                                and isinstance(value, dict)
                                and "messages" in value
                            ):
                                msg_list = value["messages"]
                                if hasattr(msg_list, "value"):
                                    msg_list = msg_list.value
                                if isinstance(msg_list, list):
                                    for msg in msg_list:
                                        if isinstance(msg, ToolMessage):
                                            tool_content = str(msg.content)
                                            tool_name = getattr(
                                                msg, "name", last_tool_name
                                            )
                                            tool_call_id = getattr(
                                                msg, "tool_call_id", None
                                            )
                                            step_id = pending_tool_ids.pop(
                                                tool_call_id, None
                                            )
                                            if not step_id:
                                                step_counter += 1
                                                step_id = f"step_{step_counter}"
                                            name, payload = format_tool_result(
                                                tool_name, tool_content
                                            )
                                            intermediate = {
                                                "type": "system_intermediate",
                                                "id": step_id,
                                                "name": name,
                                                "payload": payload,
                                                "status": "complete",
                                            }
                                            yield f"intermediate_data: {json.dumps(intermediate)}\n\n"

                    # Handle messages (token streaming)
                    elif (
                        mode == "messages"
                        and isinstance(data, tuple)
                        and len(data) == 2
                    ):
                        message, metadata = data

                        if isinstance(message, ToolMessage):
                            newline_chunk = {
                                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                "object": "chat.completion.chunk",
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": "\n\n"},
                                        "finish_reason": None,
                                    }
                                ],
                            }
                            yield f"data: {json.dumps(newline_chunk)}\n\n"
                            continue

                        content_blocks = []
                        if (
                            hasattr(message, "content_blocks")
                            and message.content_blocks
                        ):
                            content_blocks = message.content_blocks
                        elif hasattr(message, "content") and isinstance(
                            message.content, list
                        ):
                            content_blocks = message.content

                        for block in content_blocks:
                            if isinstance(block, dict):
                                block_type = block.get("type", "text")

                                if block_type == "text" or "text" in block:
                                    text = block.get("text", "")
                                    if text:
                                        chunk_data = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                            "object": "chat.completion.chunk",
                                            "choices": [
                                                {
                                                    "index": 0,
                                                    "delta": {"content": text},
                                                    "finish_reason": None,
                                                }
                                            ],
                                        }
                                        yield f"data: {json.dumps(chunk_data)}\n\n"

                                elif block_type in ("tool_call", "tool_use"):
                                    tool_name = block.get("name", "unknown")
                                    tool_args = block.get("args", {})
                                    tool_id = block.get("id")
                                    last_tool_name = tool_name

                                    step_counter += 1
                                    step_id = f"step_{step_counter}"
                                    if tool_id:
                                        pending_tool_ids[tool_id] = step_id

                                    name, payload = format_tool_call(
                                        tool_name, tool_args
                                    )
                                    intermediate = {
                                        "type": "system_intermediate",
                                        "id": step_id,
                                        "name": name,
                                        "payload": payload,
                                        "status": "in_progress",
                                    }
                                    yield f"intermediate_data: {json.dumps(intermediate)}\n\n"

            # Final chunk
            yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(resume_stream(), media_type="text/event-stream")


# =============================================================================
# Knowledge Endpoints
# =============================================================================


def _parse_md_file(md_file: Path, folder: str = None) -> dict | None:
    """Parse markdown file metadata."""
    try:
        content = md_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        title = md_file.stem.replace("-", " ").title()
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        description = ""
        for line in lines:
            if line.strip() and not line.startswith("#"):
                description = line.strip()
                break

        return {
            "id": f"{folder}/{md_file.stem}" if folder else md_file.stem,
            "title": title,
            "filename": md_file.name,
            "folder": folder,
            "description": description,
            "size": len(content),
        }
    except Exception:
        return None


@app.get("/knowledge/list")
async def list_knowledge(include_system: bool = False):
    """List all knowledge documents."""
    if not KNOWLEDGE_DIR.exists():
        return {"documents": [], "folders": {}, "count": 0}

    documents = []
    folders = {"documents": [], "skills": [], "memory": []}

    # Root documents
    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md"), key=lambda f: f.name):
        if md_file.name == "system-prompt.md" and not include_system:
            continue
        doc = _parse_md_file(md_file)
        if doc:
            documents.append(doc)

    # Subfolders
    for folder_name in ["documents", "skills", "memory"]:
        folder_path = KNOWLEDGE_DIR / folder_name
        if folder_path.exists():
            for md_file in sorted(folder_path.glob("*.md"), key=lambda f: f.name):
                doc = _parse_md_file(md_file, folder=folder_name)
                if doc:
                    folders[folder_name].append(doc)

    return {
        "documents": documents,
        "folders": folders,
        "count": len(documents) + sum(len(f) for f in folders.values()),
    }


@app.get("/knowledge/read/{filename:path}")
async def read_knowledge(filename: str):
    """Read a knowledge document."""
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    file_path = KNOWLEDGE_DIR / filename

    # Security check
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(KNOWLEDGE_DIR.resolve())):
            return {"error": "Invalid path"}
    except Exception:
        return {"error": "Invalid path"}

    if not file_path.exists():
        return {"error": f"Document '{filename}' not found"}

    content = file_path.read_text(encoding="utf-8")
    title = file_path.stem.replace("-", " ").title()
    for line in content.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    return {
        "id": file_path.stem,
        "title": title,
        "filename": file_path.name,
        "content": content,
    }


# =============================================================================
# History/Experiments Endpoints
# =============================================================================


@app.get("/history/list")
async def get_history_list(last: int = None, type: str = None):
    """List experiment history."""
    experiments = storage.search_experiments(DATA_DIR, type=type, last=last)
    return {
        "count": len(experiments),
        "experiments": [
            {
                "id": e["id"],
                "type": e["type"],
                "target": e.get("target"),
                "timestamp": e["timestamp"],
                "status": e["status"],
            }
            for e in experiments
        ],
    }


@app.get("/history/{experiment_id}")
async def get_history_detail(experiment_id: str):
    """Get experiment details."""
    experiment = storage.load_experiment(experiment_id, DATA_DIR)
    if not experiment:
        return {"error": f"Experiment '{experiment_id}' not found"}
    return experiment.to_dict()


@app.get("/history/{experiment_id}/arrays")
async def get_experiment_arrays(experiment_id: str):
    """List arrays in experiment."""
    arrays = storage.list_arrays(experiment_id, DATA_DIR)
    if arrays is None:
        return {"error": f"Experiment '{experiment_id}' not found"}
    return {"arrays": arrays}


@app.get("/history/{experiment_id}/array/{array_name}")
async def get_experiment_array(
    experiment_id: str, array_name: str, start: int = None, end: int = None
):
    """Get array data."""
    data = storage.get_array(experiment_id, array_name, DATA_DIR, start=start, end=end)
    if data is None:
        return {"error": f"Array '{array_name}' not found"}
    return {"array": array_name, "data": data, "length": len(data)}


@app.get("/history/{experiment_id}/plots")
async def get_experiment_plots(experiment_id: str):
    """List plots in experiment."""
    plots = storage.list_plots(experiment_id, DATA_DIR)
    if plots is None:
        return {"error": f"Experiment '{experiment_id}' not found"}
    return {"plots": plots}


@app.get("/history/{experiment_id}/plot/{plot_name}")
async def get_experiment_plot(experiment_id: str, plot_name: str):
    """Get plot data."""
    plot = storage.get_plot(experiment_id, plot_name, DATA_DIR)
    if plot is None:
        return {"error": f"Plot '{plot_name}' not found"}
    return plot


@app.get("/history/{experiment_id}/logs")
async def get_experiment_logs(experiment_id: str, lines: int = 100):
    """Get experiment output logs (last N lines).

    Returns real-time progress output from experiment execution.
    The log file is written during experiment execution, so this
    endpoint can be polled to monitor progress.
    """
    log_file = DATA_DIR / experiment_id / "output.log"
    if not log_file.exists():
        return {"experiment_id": experiment_id, "logs": "", "lines": 0}

    try:
        content = log_file.read_text(encoding="utf-8")
        all_lines = content.split("\n")
        last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "experiment_id": experiment_id,
            "logs": "\n".join(last_lines),
            "lines": len(last_lines),
            "total_lines": len(all_lines),
        }
    except Exception as e:
        return {"error": str(e), "logs": "", "lines": 0}


# =============================================================================
# Apparatus/Experiment Discovery Endpoints
# =============================================================================


@app.get("/experiment/capabilities")
async def get_experiment_capabilities():
    """List available experiments."""
    experiments = discovery.discover_experiments(SCRIPTS_DIR)
    return {
        "experiments": [
            {
                "name": exp.name,
                "description": exp.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "default": p.default,
                        "range": list(p.range) if p.range else None,
                        "required": p.required,
                    }
                    for p in exp.parameters
                ],
                "module_path": exp.module_path,
            }
            for exp in experiments
        ]
    }


@app.get("/experiment/schema/{name}")
async def get_experiment_schema(name: str):
    """Get experiment schema."""
    schema = discovery.get_experiment_schema(name, SCRIPTS_DIR)
    if not schema:
        return {"error": f"Experiment '{name}' not found"}
    return {
        "name": schema.name,
        "description": schema.description,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "default": p.default,
                "range": list(p.range) if p.range else None,
                "required": p.required,
            }
            for p in schema.parameters
        ],
        "module_path": schema.module_path,
    }


@app.get("/experiment/script/{name}")
async def get_experiment_script(name: str):
    """Get experiment script source."""
    schema = discovery.get_experiment_schema(name, SCRIPTS_DIR)
    if not schema:
        return {"error": f"Experiment '{name}' not found"}

    script_path = Path(schema.module_path)
    if not script_path.exists():
        return {"error": f"Script not found: {schema.module_path}"}

    content = script_path.read_text(encoding="utf-8")
    return {"name": name, "path": schema.module_path, "content": content}


# =============================================================================
# Workflow Endpoints
# =============================================================================

WORKFLOWS_DIR = ROOT_DIR / "data" / "workflows"


def _load_workflow(workflow_id: str) -> dict | None:
    """Load workflow.json for a workflow."""
    workflow_dir = WORKFLOWS_DIR / workflow_id
    workflow_file = workflow_dir / "workflow.json"
    if not workflow_file.exists():
        return None
    try:
        return json.loads(workflow_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_process_running(workflow_id: str) -> bool:
    """Check if workflow executor process is running (not zombie)."""
    pid_file = WORKFLOWS_DIR / workflow_id / "pid"
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # Check if process exists
        # Check if zombie by reading /proc/{pid}/stat
        stat_file = Path(f"/proc/{pid}/stat")
        if stat_file.exists():
            stat = stat_file.read_text()
            # Format: pid (comm) state ... - state is 3rd field
            # Z = zombie, skip parens in comm which may contain spaces
            if ") Z" in stat or ") Zs" in stat:
                return False  # Zombie process
        return True
    except (ProcessLookupError, ValueError, PermissionError, OSError):
        return False


def _get_workflow_summary(workflow_id: str) -> dict | None:
    """Get workflow summary for list view."""
    wf = _load_workflow(workflow_id)
    if not wf:
        return None

    nodes = wf.get("nodes", [])
    completed = sum(1 for n in nodes if n.get("state") == "success")
    failed = sum(1 for n in nodes if n.get("state") == "failed")
    running = sum(1 for n in nodes if n.get("state") == "running")
    total = len(nodes)

    current_node = None
    for n in nodes:
        if n.get("state") == "running":
            current_node = n.get("name") or n.get("id")
            break

    return {
        "workflow_id": wf.get("id", workflow_id),
        "name": wf.get("name", workflow_id),
        "status": wf.get("status", "unknown"),
        "progress": f"{completed}/{total}",
        "completed": completed,
        "failed": failed,
        "running": running,
        "total": total,
        "current_node": current_node,
        "process_running": _is_process_running(workflow_id),
    }


@app.get("/workflows/list")
async def list_workflows():
    """List all workflows with summary status."""
    if not WORKFLOWS_DIR.exists():
        return {"workflows": []}

    workflows = []
    for item in sorted(WORKFLOWS_DIR.iterdir(), key=lambda x: x.name, reverse=True):
        if item.is_dir() and not item.name.startswith("."):
            summary = _get_workflow_summary(item.name)
            if summary:
                workflows.append(summary)

    return {"workflows": workflows}


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get full workflow details."""
    wf = _load_workflow(workflow_id)
    if not wf:
        return {"error": f"Workflow '{workflow_id}' not found"}

    nodes = wf.get("nodes", [])
    completed = sum(1 for n in nodes if n.get("state") == "success")
    failed = sum(1 for n in nodes if n.get("state") == "failed")
    skipped = sum(1 for n in nodes if n.get("state") == "skipped")
    running = sum(1 for n in nodes if n.get("state") == "running")
    pending = sum(1 for n in nodes if n.get("state") == "pending")
    total = len(nodes)

    current_node = None
    for n in nodes:
        if n.get("state") == "running":
            current_node = {
                "id": n.get("id"),
                "name": n.get("name"),
                "state": n.get("state"),
                "run_count": n.get("run_count", 0),
            }
            break

    # Load recent history
    recent_history = []
    history_file = WORKFLOWS_DIR / workflow_id / "history.jsonl"
    if history_file.exists():
        try:
            lines = history_file.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-20:]:  # Last 20 events
                if line.strip():
                    recent_history.append(json.loads(line))
        except Exception:
            pass

    return {
        "workflow_id": wf.get("id", workflow_id),
        "name": wf.get("name", workflow_id),
        "objective": wf.get("objective", ""),
        "status": wf.get("status", "unknown"),
        "process_running": _is_process_running(workflow_id),
        "started_at": wf.get("started_at"),
        "completed_at": wf.get("completed_at"),
        "context": wf.get("context", {}),
        "progress": {
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "running": running,
            "pending": pending,
            "total": total,
        },
        "current_node": current_node,
        "nodes": [
            {
                "id": n.get("id"),
                "name": n.get("name"),
                "state": n.get("state", "pending"),
                "run_count": n.get("run_count", 0),
                "extracted": n.get("extracted"),
                "dependencies": n.get("dependencies", []),
                "experiment_id": n.get("experiment_id"),
            }
            for n in nodes
        ],
        "recent_history": recent_history,
    }


@app.get("/workflows/{workflow_id}/history")
async def get_workflow_history(workflow_id: str, last: int = 50):
    """Get workflow history events."""
    history_file = WORKFLOWS_DIR / workflow_id / "history.jsonl"
    if not history_file.exists():
        return {"error": f"Workflow '{workflow_id}' not found", "events": []}

    events = []
    try:
        lines = history_file.read_text(encoding="utf-8").strip().split("\n")
        for line in lines[-last:]:
            if line.strip():
                events.append(json.loads(line))
    except Exception as e:
        return {"error": str(e), "events": []}

    return {"workflow_id": workflow_id, "events": events, "count": len(events)}


@app.get("/workflows/{workflow_id}/plan")
async def get_workflow_plan(workflow_id: str):
    """Get workflow plan markdown."""
    plan_file = WORKFLOWS_DIR / workflow_id / "plan.md"
    if not plan_file.exists():
        return {"error": f"Plan not found for workflow '{workflow_id}'"}

    content = plan_file.read_text(encoding="utf-8")
    return {"workflow_id": workflow_id, "content": content}


@app.get("/workflows/{workflow_id}/logs")
async def get_workflow_logs(workflow_id: str, lines: int = 100):
    """Get workflow output logs (last N lines)."""
    log_file = WORKFLOWS_DIR / workflow_id / "output.log"
    if not log_file.exists():
        return {"workflow_id": workflow_id, "logs": "", "lines": 0}

    try:
        content = log_file.read_text(encoding="utf-8")
        all_lines = content.split("\n")
        last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "workflow_id": workflow_id,
            "logs": "\n".join(last_lines),
            "lines": len(last_lines),
            "total_lines": len(all_lines),
        }
    except Exception as e:
        return {"error": str(e), "logs": "", "lines": 0}


@app.get("/workflows/{workflow_id}/running")
async def get_workflow_running(workflow_id: str):
    """Check if workflow process is running."""
    import signal

    pid_file = WORKFLOWS_DIR / workflow_id / "pid"
    if not pid_file.exists():
        return {"workflow_id": workflow_id, "running": False, "pid": None}

    try:
        pid = int(pid_file.read_text().strip())
        # Check if process is alive
        os.kill(pid, 0)
        return {"workflow_id": workflow_id, "running": True, "pid": pid}
    except (ProcessLookupError, ValueError):
        # Process not running, clean up pid file
        pid_file.unlink(missing_ok=True)
        return {"workflow_id": workflow_id, "running": False, "pid": None}
    except PermissionError:
        # Process exists but we can't signal it
        return {"workflow_id": workflow_id, "running": True, "pid": pid}


@app.post("/workflows/{workflow_id}/start")
async def start_workflow(workflow_id: str):
    """Start workflow execution by spawning a QCA process."""
    import subprocess

    workflow_dir = WORKFLOWS_DIR / workflow_id
    if not workflow_dir.exists():
        return {"error": f"Workflow '{workflow_id}' not found"}

    pid_file = workflow_dir / "pid"
    log_file = workflow_dir / "output.log"

    # Check if already running
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return {"error": "Workflow is already running", "pid": pid}
        except (ProcessLookupError, ValueError):
            pid_file.unlink(missing_ok=True)

    # Clear previous log
    log_file.write_text("")

    # Spawn QCA process to execute workflow
    prompt = f"Execute workflow {workflow_id}. Read the workflow skill first, then execute it step by step."
    cmd = [
        sys.executable, "-u", "-m", "cli",  # -u for unbuffered output
        "-n", prompt,
    ]

    with open(log_file, "w") as log_handle:
        process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=str(ROOT_DIR),
            start_new_session=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},  # Ensure unbuffered
        )

    # Save PID
    pid_file.write_text(str(process.pid))

    return {"status": "started", "workflow_id": workflow_id, "pid": process.pid}


@app.post("/workflows/{workflow_id}/stop")
async def stop_workflow(workflow_id: str):
    """Stop workflow execution by killing the QCA process."""
    import signal

    pid_file = WORKFLOWS_DIR / workflow_id / "pid"
    if not pid_file.exists():
        return {"error": "Workflow is not running"}

    try:
        pid = int(pid_file.read_text().strip())
        # Kill process group to ensure all children are terminated
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        return {"status": "stopped", "workflow_id": workflow_id, "pid": pid}
    except ProcessLookupError:
        pid_file.unlink(missing_ok=True)
        return {"status": "stopped", "workflow_id": workflow_id, "message": "Process was not running"}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow and all its data."""
    import shutil

    wf_dir = WORKFLOWS_DIR / workflow_id
    if not wf_dir.exists():
        return {"error": f"Workflow '{workflow_id}' not found"}

    # Stop if running
    pid_file = wf_dir / "pid"
    if pid_file.exists():
        try:
            import signal
            pid = int(pid_file.read_text().strip())
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (ProcessLookupError, ValueError):
            pass

    shutil.rmtree(wf_dir)
    return {"status": "deleted", "workflow_id": workflow_id}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
