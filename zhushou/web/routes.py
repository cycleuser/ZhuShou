"""FastAPI routes for the ZhuShou web interface.

Endpoints:
  GET  /                 Serve index.html
  GET  /api/config       Current configuration
  GET  /api/providers    Available LLM providers
  GET  /api/models       Models for the current provider
  GET  /api/world        World context info (ModelSensor)
  POST /api/pipeline     Start a pipeline run
  POST /api/kb/crawl     Crawl a website into knowledge base
  GET  /api/kb/list      List all knowledge bases (builtin + user)
  GET  /api/kb/user      List user-created knowledge bases
  POST /api/kb/upload    Upload files to create/extend user KB
  POST /api/kb/import    Import directory into user KB
  DELETE /api/kb/{name}  Delete a user KB
  POST /api/daemon/start Start orchestration daemon
  POST /api/daemon/stop  Stop orchestration daemon
  GET  /api/daemon/snapshot  Current orchestrator state
  GET  /api/tasks        List tasks from tracker
  WS   /ws               Real-time event stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile, WebSocket, WebSocketDisconnect
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

# Orchestrator daemon state
_orchestrator: Any = None
_orchestrator_task: Any = None


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
                world_sense=_config.world_sense,
            )
            orch.run(request)
        except Exception:
            logger.exception("Pipeline run failed")
        finally:
            _running = False

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return JSONResponse({"status": "started", "output_dir": output_dir})


@router.get("/api/world")
async def get_world_info():
    """Return current world context (date/time from ModelSensor)."""
    from zhushou.utils.world_context import get_world_context

    ctx = get_world_context(_config.world_sense)
    return JSONResponse({"enabled": _config.world_sense, "context": ctx})


@router.post("/api/kb/crawl")
async def crawl_website(body: dict[str, Any]):
    """Crawl a website into the knowledge base using Huan."""
    url = body.get("url", "").strip()
    if not url:
        return JSONResponse(
            {"error": "url field is required"}, status_code=400,
        )

    name = body.get("name")
    max_pages = body.get("max_pages", 200)
    prefix = body.get("prefix")

    def _run_crawl():
        try:
            from zhushou.knowledge.kb_manager import KBManager
            from zhushou.knowledge.kb_config import KBConfig

            mgr = KBManager(KBConfig())
            pages_saved, output_dir = mgr.crawl(
                url, name=name, max_pages=max_pages, prefix=prefix,
            )
            logger.info("Crawl complete: %d pages to %s", pages_saved, output_dir)
        except Exception:
            logger.exception("KB crawl failed")

    thread = threading.Thread(target=_run_crawl, daemon=True)
    thread.start()

    return JSONResponse({"status": "crawling", "url": url})


@router.get("/api/kb/list")
async def list_kbs():
    """List all knowledge bases (built-in + user-created)."""
    try:
        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig

        mgr = KBManager(KBConfig())
        return JSONResponse({"kbs": mgr.list_sources()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/kb/user")
async def list_user_kbs():
    """List user-created knowledge bases."""
    try:
        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig

        mgr = KBManager(KBConfig())
        return JSONResponse({"kbs": mgr.list_user_kbs()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/kb/upload")
async def upload_kb(
    kb_name: str = "",
    duplicate_action: str = "skip",
    files: list[UploadFile] = [],
):
    """Upload markdown/text files to create or extend a user KB.

    Form fields:
    - kb_name: Display name for the KB (required)
    - duplicate_action: 'skip' or 'overwrite' (default: 'skip')
    - files: One or more .md / .txt files
    """
    if not kb_name:
        return JSONResponse(
            {"error": "kb_name field is required"}, status_code=400,
        )
    if not files:
        return JSONResponse(
            {"error": "At least one file is required"}, status_code=400,
        )

    # Save uploaded files to a temp dir, then delegate to KBManager
    tmp_dir = Path(tempfile.mkdtemp())
    saved_paths: list[str] = []
    try:
        for uf in files:
            target = tmp_dir / (uf.filename or "unnamed.md")
            content = await uf.read()
            target.write_bytes(content)
            saved_paths.append(str(target))

        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig

        mgr = KBManager(KBConfig())
        result = mgr.upload_files(
            kb_name, saved_paths, duplicate_action=duplicate_action,
        )
        return JSONResponse({"success": True, **result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/api/kb/import")
async def import_kb_dir(body: dict[str, Any]):
    """Import a local directory into a user KB.

    JSON body:
    - name: Display name for the KB (required)
    - dir_path: Path to the local directory (required)
    """
    name = body.get("name", "").strip()
    dir_path = body.get("dir_path", "").strip()
    if not name or not dir_path:
        return JSONResponse(
            {"error": "name and dir_path fields are required"}, status_code=400,
        )

    try:
        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig

        mgr = KBManager(KBConfig())
        result = mgr.import_directory(name, dir_path)
        return JSONResponse({"success": True, **result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/kb/{name}")
async def delete_kb(name: str):
    """Delete a user-created knowledge base by internal name."""
    if not name.startswith("user_"):
        return JSONResponse(
            {"error": "Only user-created KBs can be deleted"}, status_code=400,
        )

    try:
        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig

        mgr = KBManager(KBConfig())
        deleted = mgr.delete_user_kb(name)
        if not deleted:
            return JSONResponse(
                {"error": f"KB '{name}' not found"}, status_code=404,
            )
        return JSONResponse({"success": True, "deleted": name})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Orchestrator daemon endpoints ──────────────────────────────────

@router.post("/api/daemon/start")
async def daemon_start(body: dict[str, Any] = {}):
    """Start the orchestration daemon via the web API."""
    global _orchestrator, _orchestrator_task

    if _orchestrator is not None and _orchestrator_task and not _orchestrator_task.done():
        return JSONResponse({"error": "Daemon is already running"}, status_code=409)

    workflow_path = body.get("workflow_path", "./WORKFLOW.md")

    try:
        from zhushou.events.bus import PipelineEventBus
        from zhushou.orchestrator.loop import Orchestrator
        from zhushou.tracker import create_tracker
        from zhushou.workflow.store import WorkflowStore

        store = WorkflowStore(workflow_path)
        config = store.current_config
        tracker = create_tracker(config)

        event_bus = PipelineEventBus()
        event_bus.subscribe(_bridge.on_event)

        orch = Orchestrator(
            workflow_store=store,
            tracker=tracker,
            event_bus=event_bus,
        )
        _orchestrator = orch
        _orchestrator_task = asyncio.create_task(orch.start(), name="web-daemon")

        return JSONResponse({"status": "started", "tracker": config.tracker_kind})
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/api/daemon/stop")
async def daemon_stop():
    """Stop the orchestration daemon."""
    global _orchestrator, _orchestrator_task

    if _orchestrator is None:
        return JSONResponse({"error": "Daemon is not running"}, status_code=400)

    await _orchestrator.stop()
    if _orchestrator_task and not _orchestrator_task.done():
        _orchestrator_task.cancel()
        try:
            await _orchestrator_task
        except asyncio.CancelledError:
            pass

    _orchestrator = None
    _orchestrator_task = None
    return JSONResponse({"status": "stopped"})


@router.get("/api/daemon/snapshot")
async def daemon_snapshot():
    """Return the current orchestrator state snapshot."""
    if _orchestrator is None:
        return JSONResponse({"error": "Daemon is not running"}, status_code=400)

    snap = _orchestrator.get_snapshot()
    return JSONResponse(snap.to_dict())


@router.get("/api/tasks")
async def list_tasks(workflow_path: str = "./WORKFLOW.md"):
    """List tasks from the configured tracker."""
    try:
        from zhushou.tracker import create_tracker
        from zhushou.workflow.store import WorkflowStore

        store = WorkflowStore(workflow_path)
        config = store.current_config
        tracker = create_tracker(config)

        tasks = await tracker.fetch_candidate_tasks(
            active_states=config.active_states,
            terminal_states=[],
        )
        return JSONResponse({
            "tasks": [t.to_template_dict() for t in tasks],
            "count": len(tasks),
        })
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


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
