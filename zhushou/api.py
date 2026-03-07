"""ZhuShou - Unified Python API.

Provides ToolResult-based wrappers for programmatic usage
and agent integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResult:
    """Standardised return type for all ZhuShou API functions."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


def chat(
    message: str,
    *,
    provider: str = "ollama",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    work_dir: str = ".",
    persona_dir: str = "",
    proxy: str = "",
    timeout: int = 300,
    world_sense: bool = True,
) -> ToolResult:
    """Send a message to the AI assistant and get a response.

    Parameters
    ----------
    message : str
        The user message to send.
    provider : str
        LLM provider: ollama, openai, anthropic, deepseek, gemini.
    model : str
        Model name. Empty string uses provider default.
    api_key : str
        API key for cloud providers.
    base_url : str
        Custom API endpoint URL.
    work_dir : str
        Working directory for tool execution.
    persona_dir : str
        Path to persona configuration directory.
    proxy : str
        HTTP/HTTPS proxy URL. Empty string disables proxy.

    Returns
    -------
    ToolResult
        With data containing the assistant response text.
    """
    try:
        from zhushou import __version__
        from zhushou.llm.factory import LLMClientFactory
        from zhushou.agent.loop import AgentLoop
        from zhushou.executor.tool_executor import ToolExecutor
        from zhushou.agent.context import ContextManager
        from zhushou.tracking.tracker import TokenTracker
        from zhushou.memory.persistent import PersistentMemory
        from zhushou.persona.loader import PersonaLoader

        kwargs: dict[str, Any] = {}
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        if model:
            kwargs["model"] = model
        if proxy:
            kwargs["proxy"] = proxy
        if timeout != 300:
            kwargs["timeout"] = timeout

        client = LLMClientFactory.create_client(provider, **kwargs)
        executor = ToolExecutor(work_dir=work_dir)
        context_mgr = ContextManager(max_tokens=client.max_context_tokens)
        tracker = TokenTracker()
        memory = PersistentMemory()
        persona = PersonaLoader.load(persona_dir or work_dir)

        loop = AgentLoop(
            llm_client=client,
            tool_executor=executor,
            context_manager=context_mgr,
            memory=memory,
            tracker=tracker,
            persona=persona,
            world_sense=world_sense,
        )
        response = loop.process_message(message)

        return ToolResult(
            success=True,
            data=response,
            metadata={
                "provider": provider,
                "model": client.model,
                "usage": tracker.get_session_stats(),
                "version": __version__,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def run_pipeline(
    request: str,
    *,
    output_dir: str = "./output",
    provider: str = "ollama",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    proxy: str = "",
    full: bool = False,
    timeout: int = 300,
    kb: list[str] | None = None,
    world_sense: bool = True,
) -> ToolResult:
    """Run the 7-stage (or 9-stage with full=True) autonomous coding pipeline.

    Parameters
    ----------
    request : str
        Project description / coding request.
    output_dir : str
        Output directory for the generated project.
    provider : str
        LLM provider name.
    model : str
        Model name.
    api_key : str
        API key for cloud providers.
    base_url : str
        Custom API endpoint URL.
    proxy : str
        HTTP/HTTPS proxy URL. Empty string disables proxy.
    full : bool
        If True, run additional documentation and packaging stages (9 total).
    kb : list[str] | None
        Knowledge base sources to use (e.g. ["numpy", "flask"]).
        None disables KB context injection.

    Returns
    -------
    ToolResult
        With data containing pipeline stats (stages_completed, files_created, etc.).
    """
    try:
        from zhushou import __version__
        from zhushou.llm.factory import LLMClientFactory
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        from zhushou.utils.python_finder import find_python

        kwargs: dict[str, Any] = {}
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        if model:
            kwargs["model"] = model
        if proxy:
            kwargs["proxy"] = proxy
        if timeout != 300:
            kwargs["timeout"] = timeout

        client = LLMClientFactory.create_client(provider, **kwargs)
        python_path = find_python()

        orchestrator = PipelineOrchestrator(
            llm_client=client,
            work_dir=output_dir,
            python_path=python_path,
            full_mode=full,
            kb_collections=kb,
            world_sense=world_sense,
        )
        stats = orchestrator.run(request)

        return ToolResult(
            success=stats.get("tests_passed", "") == "All passed",
            data=stats,
            metadata={
                "provider": provider,
                "model": client.model,
                "version": __version__,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def search_pypi(
    query: str,
    *,
    max_results: int = 5,
) -> ToolResult:
    """Search PyPI for Python packages.

    Parameters
    ----------
    query : str
        Search query string.
    max_results : int
        Maximum number of results to return.

    Returns
    -------
    ToolResult
        With data containing list of package info dicts.
    """
    try:
        from zhushou import __version__
        import httpx

        url = "https://pypi.org/pypi"
        # Use trust_env=False to avoid system proxy env var issues
        results = []
        try:
            with httpx.Client(trust_env=False, timeout=10.0, follow_redirects=True) as client:
                resp = client.get(f"{url}/{query}/json")
                if resp.status_code == 200:
                    data = resp.json()
                    info = data.get("info", {})
                    results.append({
                        "name": info.get("name", query),
                        "version": info.get("version", ""),
                        "summary": info.get("summary", ""),
                        "home_page": info.get("home_page", ""),
                        "author": info.get("author", ""),
                    })
        except Exception:
            pass

        # Search via simple API
        if len(results) < max_results:
            try:
                with httpx.Client(trust_env=False, timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(
                        "https://pypi.org/search/",
                        params={"q": query},
                    )
                if resp.status_code == 200:
                    import re
                    pattern = r'class="package-snippet__name">([^<]+)</span>'
                    version_pattern = r'class="package-snippet__version">([^<]+)</span>'
                    desc_pattern = r'class="package-snippet__description">([^<]+)</p>'
                    names = re.findall(pattern, resp.text)
                    versions = re.findall(version_pattern, resp.text)
                    descs = re.findall(desc_pattern, resp.text)
                    existing = {r["name"] for r in results}
                    for i, name in enumerate(names):
                        if name not in existing and len(results) < max_results:
                            results.append({
                                "name": name.strip(),
                                "version": versions[i].strip() if i < len(versions) else "",
                                "summary": descs[i].strip() if i < len(descs) else "",
                            })
            except Exception:
                pass

        return ToolResult(
            success=True,
            data=results[:max_results],
            metadata={
                "query": query,
                "count": len(results[:max_results]),
                "version": __version__,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Knowledge Base API ────────────────────────────────────────────────

def kb_list(**kwargs: Any) -> ToolResult:
    """List all available knowledge base sources with status."""
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        return ToolResult(success=True, data=mgr.list_sources())
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_download(source: str, **kwargs: Any) -> ToolResult:
    """Download official docs for a knowledge base source."""
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        saved, errors = mgr.download(source)
        return ToolResult(
            success=len(errors) == 0,
            data={"saved": saved, "errors": errors},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_index(source: str, **kwargs: Any) -> ToolResult:
    """Index downloaded docs for a knowledge base source."""
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        chunks, files = mgr.index(source)
        return ToolResult(
            success=files > 0,
            data={"chunks": chunks, "files": files},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_search(query: str, *, sources: list[str] | None = None, **kwargs: Any) -> ToolResult:
    """Search the indexed knowledge base."""
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        results = mgr.search(query, collections=sources)
        return ToolResult(success=True, data=results)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_crawl(
    url: str,
    *,
    name: str | None = None,
    max_pages: int = 200,
    prefix: str | None = None,
) -> ToolResult:
    """Crawl a website into the knowledge base using Huan.

    Parameters
    ----------
    url : str
        URL to crawl.
    name : str | None
        Source name. Defaults to the domain.
    max_pages : int
        Maximum pages to crawl.
    prefix : str | None
        Only crawl URLs with this path prefix.

    Returns
    -------
    ToolResult
        With data containing pages_saved and output_dir.
    """
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        pages_saved, output_dir = mgr.crawl(
            url, name=name, max_pages=max_pages, prefix=prefix,
        )
        return ToolResult(
            success=pages_saved > 0,
            data={"pages_saved": pages_saved, "output_dir": output_dir},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_upload(
    name: str,
    file_paths: list[str],
    *,
    duplicate_action: str = "skip",
) -> ToolResult:
    """Upload markdown/text files to create or extend a user KB.

    Parameters
    ----------
    name : str
        Human-readable display name for the KB.
    file_paths : list[str]
        Paths to ``.md`` / ``.txt`` files.
    duplicate_action : str
        ``"skip"`` (default) or ``"overwrite"`` existing files.

    Returns
    -------
    ToolResult
        With data containing internal_name, saved, skipped, errors.
    """
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        result = mgr.upload_files(name, file_paths, duplicate_action=duplicate_action)
        return ToolResult(
            success=result["saved"] > 0 or result["skipped"] > 0,
            data=result,
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_import_dir(
    name: str,
    dir_path: str,
) -> ToolResult:
    """Recursively import markdown/text files from a directory into a user KB.

    Parameters
    ----------
    name : str
        Human-readable display name for the KB.
    dir_path : str
        Path to the source directory.

    Returns
    -------
    ToolResult
        With data containing internal_name, saved, errors.
    """
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        result = mgr.import_directory(name, dir_path)
        return ToolResult(success=result["saved"] > 0, data=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_delete(internal_name: str) -> ToolResult:
    """Delete a user-created knowledge base.

    Parameters
    ----------
    internal_name : str
        Internal name of the KB (``user_``-prefixed).

    Returns
    -------
    ToolResult
        With data containing deleted status.
    """
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        deleted = mgr.delete_user_kb(internal_name)
        return ToolResult(
            success=deleted,
            data={"deleted": deleted, "name": internal_name},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def kb_list_user() -> ToolResult:
    """List all user-created knowledge bases.

    Returns
    -------
    ToolResult
        With data containing list of user KB metadata dicts.
    """
    try:
        from zhushou.knowledge.kb_manager import KBManager

        mgr = KBManager()
        return ToolResult(success=True, data=mgr.list_user_kbs())
    except Exception as e:
        return ToolResult(success=False, error=str(e))
