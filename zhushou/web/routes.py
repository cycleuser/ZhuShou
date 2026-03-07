"""FastAPI routes for the ZhuShou web interface.

Endpoints:
  GET  /                 Serve index.html
  GET  /api/config       Current configuration
  GET  /api/providers    Available LLM providers
  GET  /api/models       Models for the current provider
  POST /api/pipeline     Start a pipeline run
  WS   /ws               Real-time event stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from zhushou.config.manager import ZhuShouConfig
from zhushou.events.bus import PipelineEventBus
from zhushou.web.bridge import WebEventBridge

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level state (set by app.py at startup)
_config: ZhuShouConfig = ZhuShouConfig()
_bridge: WebEventBridge = WebEventBridge()
_running: bool = False
_static_dir = Path(__file__).parent / "static"


def configure(config: ZhuShouConfig, bridge: WebEventBridge) -> None:
    """Called once at startup to inject config and bridge."""
    global _config, _bridge
    _config = config
    _bridge = bridge


# ── Static files ───────────────────────────────────────────────────

@router.get("/", include_in_schema=False)
async def index():
    return FileResponse(_static_dir / "index.html")


@router.get("/style.css", include_in_schema=False)
async def style():
    return FileResponse(_static_dir / "style.css", media_type="text/css")


@router.get("/app.js", include_in_schema=False)
async def script():
    return FileResponse(
        _static_dir / "app.js", media_type="application/javascript",
    )


# ── API endpoints ──────────────────────────────────────────────────

@router.get("/api/config")
async def get_config():
    return JSONResponse(_config.to_display_dict())


@router.get("/api/providers")
async def get_providers():
    try:
        from zhushou.llm.factory import LLMClientFactory
        providers = LLMClientFactory.list_providers()
    except Exception:
        providers = ["ollama", "openai", "anthropic", "deepseek", "gemini"]
    return JSONResponse(providers)


@router.get("/api/models")
async def get_models():
    try:
        from zhushou.llm.factory import LLMClientFactory

        kwargs: dict[str, Any] = {}
        if _config.base_url:
            kwargs["base_url"] = _config.base_url
        if _config.api_key:
            kwargs["api_key"] = _config.api_key

        client = LLMClientFactory.create_client(_config.provider, **kwargs)
        models = client.list_models()
        data = []
        for m in models:
            if isinstance(m, str):
                data.append({"name": m})
            else:
                data.append({
                    "name": getattr(m, "name", str(m)),
                    "size": getattr(m, "size", ""),
                    "provider": getattr(m, "provider", ""),
                })
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/pipeline")
async def start_pipeline(body: dict[str, Any]):
    global _running

    if _running:
        return JSONResponse(
            {"error": "A pipeline is already running"}, status_code=409,
        )

    request = body.get("request", "").strip()
    if not request:
        return JSONResponse(
            {"error": "request field is required"}, status_code=400,
        )

    output_dir = body.get("output_dir", "./output")
    provider = body.get("provider", _config.provider)
    model = body.get("model", _config.model)

    _running = True

    def _run_pipeline():
        global _running
        try:
            from zhushou.llm.factory import LLMClientFactory
            from zhushou.pipeline.orchestrator import PipelineOrchestrator
            from zhushou.utils.python_finder import find_python

            bus = PipelineEventBus()
            bus.subscribe(_bridge.on_event)

            kwargs: dict[str, Any] = {}
            if _config.api_key:
                kwargs["api_key"] = _config.api_key
            if _config.base_url:
                kwargs["base_url"] = _config.base_url
            if _config.proxy:
                kwargs["proxy"] = _config.proxy
            if model:
                kwargs["model"] = model

            client = LLMClientFactory.create_client(provider, **kwargs)
            python_path = _config.python_path or find_python()

            orch = PipelineOrchestrator(
                llm_client=client,
                work_dir=output_dir,
                python_path=python_path,
                event_bus=bus,
            )
            orch.run(request)
        except Exception:
            logger.exception("Pipeline run failed")
        finally:
            _running = False

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return JSONResponse({"status": "started", "output_dir": output_dir})


# ── WebSocket ──────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    q = await _bridge.add_client()
    try:
        while True:
            msg = await q.get()
            await ws.send_text(msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("WebSocket error", exc_info=True)
    finally:
        await _bridge.remove_client(q)
