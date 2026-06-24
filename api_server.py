#!/usr/bin/env python3
"""Deployment-agnostic HTTP API for the Hermes agent.

Unlike ``space_app.py`` (which only serves the static landing page for a
Hugging Face Space), this module exposes the *agent itself* over HTTP so it can
be dropped into any environment — a Hugging Face Space, a container on
Render/Fly/Railway, a bare VM behind nginx, a Kubernetes pod, etc. There are no
platform-specific assumptions: everything is configured through environment
variables and the listening host/port are fully overridable.

It is intentionally dependency-free (Python standard library only, on top of
the agent's own dependencies), so it adds nothing new to install.

Endpoints
---------
GET  /health
    Liveness probe. Always 200 once the process is up.

GET  /
    Plain JSON describing the service and its routes.

POST /v1/agent
    Native Hermes endpoint. Body:
        {
          "message": "your prompt",                 # required
          "conversation_history": [ {role, content}, ... ],  # optional
          "system": "system prompt override",       # optional
          "model": "anthropic/claude-opus-4.6",     # optional
          "enabled_toolsets":  "web,development" | ["web", ...],  # optional
          "disabled_toolsets": "...",               # optional
          "max_iterations": 60                       # optional
        }
    Returns the full agent result:
        { final_response, messages, api_calls, completed, partial, interrupted }

POST /v1/chat/completions
    OpenAI-compatible Chat Completions endpoint (non-streaming). Lets any
    OpenAI client/SDK talk to Hermes as a drop-in backend. Body is the standard
    OpenAI shape ({ model, messages: [...] }); the response is a standard
    ChatCompletion object, with agent metadata under the "hermes" key.

Configuration (environment variables)
-------------------------------------
HOST                  Bind address                 (default 0.0.0.0)
PORT                  Bind port                    (default 8000; HF sets 7860)
HERMES_MODEL          Default model                (default anthropic/claude-opus-4.6)
HERMES_API_BASE       Upstream model base URL      (default OpenRouter via the agent)
OPENROUTER_API_KEY    Upstream model API key       (read by the agent itself)
HERMES_ENABLED_TOOLSETS   Default enabled toolsets (comma-separated)
HERMES_DISABLED_TOOLSETS  Default disabled toolsets (comma-separated)
HERMES_MAX_ITERATIONS     Default tool-calling iterations (default 60)
HERMES_SERVER_API_KEY     If set, callers must send this as a Bearer token
                          (Authorization: Bearer <key>) or X-API-Key header.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration (read once at import; all overridable via env)
# ---------------------------------------------------------------------------
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
DEFAULT_MODEL = os.environ.get("HERMES_MODEL", "anthropic/claude-opus-4.6")
DEFAULT_API_BASE = os.environ.get("HERMES_API_BASE") or None
DEFAULT_ENABLED = os.environ.get("HERMES_ENABLED_TOOLSETS") or None
DEFAULT_DISABLED = os.environ.get("HERMES_DISABLED_TOOLSETS") or None
DEFAULT_MAX_ITERATIONS = int(os.environ.get("HERMES_MAX_ITERATIONS", "60"))
SERVER_API_KEY = os.environ.get("HERMES_SERVER_API_KEY") or None
MAX_BODY_BYTES = int(os.environ.get("HERMES_MAX_BODY_BYTES", str(4 * 1024 * 1024)))


def _as_list(value: Any) -> Optional[List[str]]:
    """Normalise a toolset spec (comma string or list) into a list or None."""
    if value is None:
        return None
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",") if part.strip()]
        return items or None
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value if str(v).strip()]
        return items or None
    return None


# The AIAgent class is imported once and cached. The import MUST happen on the
# main thread: importing the agent pulls in tools.browser_tool, which registers
# SIGINT/SIGTERM handlers at import time, and signal.signal() only works on the
# main thread. main() warms this at startup; if it hasn't run (e.g. embedded
# use), the first call here still works as long as it's on the main thread.
_AGENT_CLS = None
_AGENT_IMPORT_ERROR: Optional[BaseException] = None


def load_agent_class():
    """Import and cache the AIAgent class (idempotent). Raises if unavailable."""
    global _AGENT_CLS, _AGENT_IMPORT_ERROR
    if _AGENT_CLS is None and _AGENT_IMPORT_ERROR is None:
        try:
            from run_agent import AIAgent
            _AGENT_CLS = AIAgent
        except BaseException as exc:  # noqa: BLE001 - surfaced to caller below
            _AGENT_IMPORT_ERROR = exc
    if _AGENT_IMPORT_ERROR is not None:
        raise RuntimeError(f"agent backend unavailable: {_AGENT_IMPORT_ERROR}")
    return _AGENT_CLS


def build_agent(
    *,
    model: Optional[str] = None,
    enabled_toolsets: Any = None,
    disabled_toolsets: Any = None,
    max_iterations: Optional[int] = None,
    system_prompt: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """Construct a fresh AIAgent for a single request.

    A new agent per request mirrors the gateway pattern in this repo and keeps
    concurrent requests free of shared mutable state. The class is loaded via the
    cached, main-thread-warmed importer so /health stays up even if the agent's
    heavy dependencies are unavailable.
    """
    AIAgent = load_agent_class()

    return AIAgent(
        model=model or DEFAULT_MODEL,
        base_url=DEFAULT_API_BASE,  # None -> agent defaults to OpenRouter
        enabled_toolsets=_as_list(enabled_toolsets if enabled_toolsets is not None else DEFAULT_ENABLED),
        disabled_toolsets=_as_list(disabled_toolsets if disabled_toolsets is not None else DEFAULT_DISABLED),
        max_iterations=int(max_iterations) if max_iterations else DEFAULT_MAX_ITERATIONS,
        ephemeral_system_prompt=system_prompt,
        quiet_mode=True,
        skip_context_files=True,
        platform="api",
        session_id=session_id or str(uuid.uuid4()),
    )


def run_agent_turn(
    message: str,
    *,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    system: Optional[str] = None,
    model: Optional[str] = None,
    enabled_toolsets: Any = None,
    disabled_toolsets: Any = None,
    max_iterations: Optional[int] = None,
) -> Dict[str, Any]:
    """Run one full agent turn and return the raw result dict."""
    agent = build_agent(
        model=model,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
        max_iterations=max_iterations,
        system_prompt=system,
    )
    return agent.run_conversation(
        message,
        system_message=system,
        conversation_history=conversation_history,
    )


def _split_openai_messages(messages: List[Dict[str, Any]]) -> tuple:
    """Split an OpenAI-style messages array into (system, history, last_user).

    All leading/system messages are merged into a single system string; the
    final user message becomes the prompt; everything before it (minus system
    turns) becomes the conversation history Hermes consumes.
    """
    system_parts: List[str] = []
    convo: List[Dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            if content:
                system_parts.append(content if isinstance(content, str) else json.dumps(content))
        else:
            convo.append({"role": role, "content": content})

    last_user = ""
    if convo and convo[-1].get("role") == "user":
        last_user = convo.pop()["content"]
        if not isinstance(last_user, str):
            last_user = json.dumps(last_user)

    system = "\n\n".join(system_parts) if system_parts else None
    history = convo or None
    return system, history, last_user


class HermesHandler(BaseHTTPRequestHandler):
    server_version = "HermesAPI/1.0"

    # -- helpers ------------------------------------------------------------
    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _authorized(self) -> bool:
        if not SERVER_API_KEY:
            return True
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and auth[7:].strip() == SERVER_API_KEY:
            return True
        if self.headers.get("X-API-Key", "").strip() == SERVER_API_KEY:
            return True
        return False

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter logs
        print("hermes-api: " + (fmt % args), flush=True)

    # -- routing ------------------------------------------------------------
    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-API-Key")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if path == "/":
            self._send_json(200, {
                "service": "hermes-agent",
                "description": "HTTP API around the Hermes agent. Platform-agnostic.",
                "endpoints": {
                    "GET /health": "liveness probe",
                    "POST /v1/agent": "native Hermes turn",
                    "POST /v1/chat/completions": "OpenAI-compatible chat completions",
                },
                "default_model": DEFAULT_MODEL,
                "auth_required": bool(SERVER_API_KEY),
            })
            return
        self._send_json(404, {"error": "not found", "path": path})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if not self._authorized():
            self._send_json(401, {"error": "unauthorized"})
            return
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json(413 if "too large" in str(exc) else 400,
                            {"error": f"invalid request body: {exc}"})
            return

        try:
            if path == "/v1/agent":
                self._handle_agent(body)
            elif path == "/v1/chat/completions":
                self._handle_openai(body)
            else:
                self._send_json(404, {"error": "not found", "path": path})
        except Exception as exc:  # never leak a stack trace to the client
            self.log_message("error handling %s: %s", path, exc)
            self._send_json(500, {"error": "internal error", "detail": str(exc)})

    # -- handlers -----------------------------------------------------------
    def _handle_agent(self, body: Dict[str, Any]) -> None:
        message = body.get("message")
        if not message or not isinstance(message, str):
            self._send_json(400, {"error": "'message' (string) is required"})
            return
        result = run_agent_turn(
            message,
            conversation_history=body.get("conversation_history"),
            system=body.get("system"),
            model=body.get("model"),
            enabled_toolsets=body.get("enabled_toolsets"),
            disabled_toolsets=body.get("disabled_toolsets"),
            max_iterations=body.get("max_iterations"),
        )
        self._send_json(200, result)

    def _handle_openai(self, body: Dict[str, Any]) -> None:
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            self._send_json(400, {"error": "'messages' (non-empty array) is required"})
            return
        if body.get("stream"):
            # Streaming is intentionally unsupported; the agent loop is not
            # token-streamed. Clients should request stream=false.
            self._send_json(400, {"error": "streaming is not supported; set stream=false"})
            return

        system, history, last_user = _split_openai_messages(messages)
        if not last_user:
            self._send_json(400, {"error": "the final message must be a user message"})
            return

        result = run_agent_turn(
            last_user,
            conversation_history=history,
            system=system,
            model=body.get("model"),
            max_iterations=body.get("max_iterations"),
        )
        model_name = body.get("model") or DEFAULT_MODEL
        self._send_json(200, {
            "id": "chatcmpl-" + uuid.uuid4().hex,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("final_response") or "",
                },
                "finish_reason": "stop" if result.get("completed") else "length",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "hermes": {
                "api_calls": result.get("api_calls"),
                "completed": result.get("completed"),
                "partial": result.get("partial"),
                "interrupted": result.get("interrupted"),
            },
        })


def main() -> None:
    # Warm the agent import on the MAIN thread before serving. The agent registers
    # signal handlers at import time, which is only valid on the main thread; doing
    # it here keeps the threaded request handlers from tripping over it. A failure
    # is non-fatal — /health and / still respond, and agent endpoints report it.
    try:
        load_agent_class()
        print("Hermes agent backend loaded.", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: agent backend failed to load ({exc}); "
              f"health/info still served, agent endpoints will return 500.", flush=True)

    server = ThreadingHTTPServer((HOST, PORT), HermesHandler)
    auth = "on" if SERVER_API_KEY else "off"
    print(
        f"Hermes API listening on http://{HOST}:{PORT} "
        f"(model={DEFAULT_MODEL}, auth={auth})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
