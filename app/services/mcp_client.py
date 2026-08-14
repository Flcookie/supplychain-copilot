"""
Copilot-side MCP client.

Spawns ``mcp_server.server`` over stdio, then uses the standard MCP session API:
  list_tools() → discover tool catalog (descriptions feed routing)
  call_tool()  → execute query_policy / query_kpi

LangGraph nodes call the sync helpers below; a background event loop keeps one
stdio session warm so Pinecone/SQLite init is not repeated every turn.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpToolError(RuntimeError):
    """Raised when an MCP tool returns isError=true (standard protocol error)."""

    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"MCP tool '{tool_name}' error: {message}")


@dataclass(frozen=True)
class McpToolInfo:
    name: str
    description: str
    input_schema: dict[str, Any]


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _server_params() -> StdioServerParameters:
    root = _project_root()
    env = os.environ.copy()
    env["MCP_STDIO_MODE"] = "1"
    # Ensure subprocess can import project packages.
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = root if not existing else os.pathsep.join([root, existing])
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=root,
        env=env,
    )


def _parse_tool_payload(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list, int, float, bool)):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _content_to_text(result: Any) -> str:
    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


class _PersistentMcpSession:
    """One stdio MCP subprocess + ClientSession, owned by a dedicated asyncio loop."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="mcp-client-loop", daemon=True)
        self._ready = threading.Event()
        self._error: BaseException | None = None
        self._session: ClientSession | None = None
        self._stack = None  # AsyncExitStack-like via nested context managers
        self._cm_stdio = None
        self._cm_session = None
        self._lock = asyncio.Lock()
        self._thread.start()
        if not self._ready.wait(timeout=120):
            raise TimeoutError("MCP stdio server failed to start within 120s.")
        if self._error is not None:
            raise RuntimeError(f"MCP stdio server failed to start: {self._error}") from self._error

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect())
            self._ready.set()
            self._loop.run_forever()
        except BaseException as exc:  # noqa: BLE001 — surface startup failures
            self._error = exc
            self._ready.set()

    async def _connect(self) -> None:
        params = _server_params()
        self._cm_stdio = stdio_client(params)
        read, write = await self._cm_stdio.__aenter__()
        self._cm_session = ClientSession(read, write)
        self._session = await self._cm_session.__aenter__()
        await self._session.initialize()

    def run(self, coro):
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=180)

    async def list_tools(self) -> list[McpToolInfo]:
        assert self._session is not None
        async with self._lock:
            listed = await self._session.list_tools()
        tools: list[McpToolInfo] = []
        for tool in listed.tools:
            tools.append(
                McpToolInfo(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=dict(tool.inputSchema or {}),
                )
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        assert self._session is not None
        async with self._lock:
            result = await self._session.call_tool(name, arguments=arguments or {})
        text = _content_to_text(result)
        if getattr(result, "isError", False):
            raise McpToolError(name, text or "unknown tool error")
        return _parse_tool_payload(text)


_SESSION: _PersistentMcpSession | None = None
_SESSION_LOCK = threading.Lock()


def get_mcp_session() -> _PersistentMcpSession:
    global _SESSION
    with _SESSION_LOCK:
        if _SESSION is None:
            _SESSION = _PersistentMcpSession()
        return _SESSION


def list_tools() -> list[McpToolInfo]:
    """MCP list_tools() — Copilot discovers capabilities + descriptions."""
    return get_mcp_session().run(get_mcp_session().list_tools())


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    """MCP call_tool() — execute a registered server tool."""
    return get_mcp_session().run(get_mcp_session().call_tool(name, arguments))


def format_tools_for_router(tools: list[McpToolInfo] | None = None) -> str:
    """Compact catalog injected into the router prompt (descriptions = routing signal)."""
    catalog = tools if tools is not None else list_tools()
    if not catalog:
        return "(no MCP tools available)"
    lines = []
    for tool in catalog:
        desc = " ".join((tool.description or "").split())
        if len(desc) > 280:
            desc = desc[:277] + "..."
        lines.append(f"- {tool.name}: {desc}")
    return "\n".join(lines)


def reset_mcp_session_for_tests() -> None:
    """Test helper — drop the cached session (does not kill the subprocess cleanly)."""
    global _SESSION
    with _SESSION_LOCK:
        _SESSION = None
