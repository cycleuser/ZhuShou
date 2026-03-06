"""Synchronous Ollama REST API wrapper using httpx."""

import json
import time
from dataclasses import dataclass
from typing import Callable

import httpx


@dataclass
class ModelInfo:
    name: str
    size: float  # in GB
    modified: str


class OllamaClient:
    """Client for the Ollama REST API."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0))

    def check_connection(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except httpx.ConnectError:
            return False

    def list_models(self) -> list[ModelInfo]:
        """List available models from Ollama."""
        resp = self._client.get(f"{self.base_url}/api/tags")
        resp.raise_for_status()
        data = resp.json()
        models = []
        for m in data.get("models", []):
            size_gb = m.get("size", 0) / (1024**3)
            models.append(
                ModelInfo(
                    name=m["name"],
                    size=round(size_gb, 1),
                    modified=m.get("modified_at", "")[:10],
                )
            )
        # Sort by size descending
        models.sort(key=lambda x: x.size, reverse=True)
        return models

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """Send a chat request with streaming.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            temperature: Sampling temperature
            on_token: Optional callback called with each token for live display

        Returns:
            Full response text concatenated from all streamed chunks.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": 32768,
            },
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self._stream_chat(payload, on_token)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError) as e:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    time.sleep(wait)
                else:
                    raise ConnectionError(
                        f"Failed to connect to Ollama after {max_retries} attempts: {e}"
                    ) from e
        return ""  # unreachable

    def _stream_chat(
        self,
        payload: dict,
        on_token: Callable[[str], None] | None,
    ) -> str:
        full_response = []
        with self._client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if chunk.get("done"):
                    break
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_response.append(token)
                    if on_token:
                        on_token(token)
        return "".join(full_response)

    def close(self):
        self._client.close()
