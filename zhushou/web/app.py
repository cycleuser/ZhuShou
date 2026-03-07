"""FastAPI application factory and launcher for ZhuShou web interface."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI

from zhushou.config.manager import ZhuShouConfig
from zhushou.web.bridge import WebEventBridge
from zhushou.web.routes import configure, router

logger = logging.getLogger(__name__)


def create_app(config: ZhuShouConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = ZhuShouConfig.load()

    app = FastAPI(
        title="ZhuShou Web",
        description="AI-powered development assistant — web interface",
    )

    bridge = WebEventBridge()

    @app.on_event("startup")
    async def on_startup():
        bridge.set_loop(asyncio.get_running_loop())

    configure(config, bridge)
    app.include_router(router)

    return app


def launch_web(
    host: str = "127.0.0.1",
    port: int = 8765,
    config: Any | None = None,
) -> None:
    """Launch the web interface with uvicorn.

    Called from ``zhushou.cli._cmd_web()``.
    """
    import uvicorn

    if config is None or not isinstance(config, ZhuShouConfig):
        config = ZhuShouConfig.load()

    app = create_app(config)

    print(f"ZhuShou Web running at http://{host}:{port}")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
