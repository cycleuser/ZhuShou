"""Jinja2-based prompt builder for task-scoped pipeline prompts.

Renders the WORKFLOW.md template body with strict variable checking,
injecting task metadata and attempt context -- mirroring Symphony's
``prompt_builder.ex`` which uses Solid templates with
``strict_variables: true``.
"""

from __future__ import annotations

import logging
from typing import Any

import jinja2

from zhushou.tracker.task import Task

logger = logging.getLogger(__name__)

_DEFAULT_PROMPT = (
    "You are working on task `{{ task.identifier }}`.\n"
    "Title: {{ task.title }}\n"
    "{% if task.description %}{{ task.description }}{% endif %}\n"
    "{% if attempt %}This is retry attempt #{{ attempt }}. "
    "Resume from workspace state. Do not restart from scratch.{% endif %}"
)


class PromptRenderError(Exception):
    """Raised when a Jinja2 template cannot be rendered."""


def render_prompt(
    template_source: str,
    task: Task,
    *,
    attempt: int | None = None,
    extra_context: dict[str, Any] | None = None,
) -> str:
    """Render *template_source* with task context.

    Parameters
    ----------
    template_source:
        Jinja2 template string (the WORKFLOW.md body).  If empty or
        whitespace-only, the built-in default template is used.
    task:
        The task being worked on -- converted to a dict for the template.
    attempt:
        Retry attempt number (``None`` for first run, 1+ for retries).
    extra_context:
        Additional variables to expose in the template.

    Raises
    ------
    PromptRenderError
        If the template contains unknown variables or syntax errors.
    """
    source = template_source.strip() if template_source else ""
    if not source:
        source = _DEFAULT_PROMPT

    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
    )

    try:
        tmpl = env.from_string(source)
    except jinja2.TemplateSyntaxError as exc:
        raise PromptRenderError(f"Template syntax error: {exc}") from exc

    context: dict[str, Any] = {
        "task": task.to_template_dict(),
        "attempt": attempt,
    }
    if extra_context:
        context.update(extra_context)

    try:
        return tmpl.render(context)
    except jinja2.UndefinedError as exc:
        raise PromptRenderError(f"Unknown template variable: {exc}") from exc
    except jinja2.TemplateError as exc:
        raise PromptRenderError(f"Template render error: {exc}") from exc
