"""Comparison testing framework for baseline vs enhanced evaluation."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from zhushou.llm.base import LLMResponse, TokenUsage


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    benchmark_name: str
    total_samples: int
    correct: int
    accuracy: float
    latencies: list[float]
    avg_latency: float
    strategy_used: str
    errors: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark_name,
            "total": self.total_samples,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "avg_latency": round(self.avg_latency, 3),
            "errors": self.errors,
            "strategy": self.strategy_used,
            "details": self.details,
        }


@dataclass
class ComparisonReport:
    """Report of comparison between baseline and enhanced performance."""

    timestamp: str
    model_name: str
    benchmarks_tested: list[str]
    baseline_results: dict[str, Any]
    enhanced_results: dict[str, Any]
    improvement_summary: dict[str, Any]
    config_used: dict[str, Any]
    total_time_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "model": self.model_name,
            "benchmarks": self.benchmarks_tested,
            "baseline": self.baseline_results,
            "enhanced": self.enhanced_results,
            "improvement": self.improvement_summary,
            "config": self.config_used,
            "total_time_seconds": round(self.total_time_seconds, 2),
        }

    def save(self, path: Path | str) -> None:
        """Save report to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class ComparisonRunner:
    """Runner for comparing baseline vs enhanced performance."""

    BENCHMARK_CLASSES = {
        "mmlu": None,
        "gsm8k": None,
        "hellaswag": None,
        "truthfulqa": None,
        "arc": None,
    }

    def __init__(self, llm_client: Any, model_name: str = "unknown"):
        self._client = llm_client
        self._model_name = model_name

    def _get_benchmark_class(self, name: str):
        """Lazily load benchmark class to avoid circular imports."""
        if self.BENCHMARK_CLASSES[name] is None:
            if name == "mmlu":
                from .benchmarks import MMLU
                self.BENCHMARK_CLASSES[name] = MMLU
            elif name == "gsm8k":
                from .benchmarks import GSM8K
                self.BENCHMARK_CLASSES[name] = GSM8K
            elif name == "hellaswag":
                from .benchmarks import Hellaswag
                self.BENCHMARK_CLASSES[name] = Hellaswag
            elif name == "truthfulqa":
                from .benchmarks import TruthfulQA
                self.BENCHMARK_CLASSES[name] = TruthfulQA
            elif name == "arc":
                from .benchmarks import ARC
                self.BENCHMARK_CLASSES[name] = ARC
        return self.BENCHMARK_CLASSES[name]

    def run_comparison(
        self,
        benchmarks: list[str] | None = None,
        baseline_config: dict[str, Any] | None = None,
        enhanced_config: dict[str, Any] | None = None,
        max_samples: int = 30,
        output_dir: Path | str | None = None,
    ) -> ComparisonReport:
        """Run full comparison between baseline and enhanced modes."""
        from .benchmarks import BenchmarkRunner
        from .enhancer import LLMEnhancer, EnhancementConfig

        start_time = time.time()

        if benchmarks is None:
            benchmarks = ["mmlu", "gsm8k", "hellaswag"]

        if baseline_config is None:
            baseline_config = {}

        if enhanced_config is None:
            enhanced_config = {
                "use_cot": True,
                "use_self_consistency": True,
                "use_constitutional": True,
                "n_samples": 5,
            }

        baseline_runner = BenchmarkRunner(
            llm_client=self._client,
            max_samples=max_samples,
        )

        baseline_results = {}
        for benchmark_name in benchmarks:
            dataset_class = self._get_benchmark_class(benchmark_name)
            if dataset_class is None:
                continue
            dataset = dataset_class()
            result = baseline_runner.run(
                dataset=dataset,
                prompt_strategy="zero_shot",
                temperature=baseline_config.get("temperature", 0.3),
            )
            baseline_results[benchmark_name] = result.to_dict()

        config = EnhancementConfig(**enhanced_config)
        enhancer = LLMEnhancer(self._client, config)
        enhancer_runner = BenchmarkRunner(
            llm_client=EnhancedLLMClient(enhancer),
            max_samples=max_samples,
        )

        enhanced_results = {}
        for benchmark_name in benchmarks:
            dataset_class = self._get_benchmark_class(benchmark_name)
            if dataset_class is None:
                continue
            dataset = dataset_class()
            strategy = "cot" if enhanced_config.get("use_cot", False) else "zero_shot"
            result = enhancer_runner.run(
                dataset=dataset,
                prompt_strategy=strategy,
                temperature=enhanced_config.get("temperature", 0.3),
            )
            enhanced_results[benchmark_name] = result.to_dict()

        improvement = self._calculate_improvement(baseline_results, enhanced_results)

        total_time = time.time() - start_time

        return ComparisonReport(
            timestamp=datetime.now().isoformat(),
            model_name=self._model_name,
            benchmarks_tested=benchmarks,
            baseline_results=baseline_results,
            enhanced_results=enhanced_results,
            improvement_summary=improvement,
            config_used=enhanced_config,
            total_time_seconds=total_time,
        )

    def _calculate_improvement(
        self,
        baseline: dict[str, Any],
        enhanced: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate improvement between baseline and enhanced."""
        summary = {}

        for benchmark_name in baseline:
            if benchmark_name not in enhanced:
                continue

            b_acc = baseline[benchmark_name].get("accuracy", 0)
            e_acc = enhanced[benchmark_name].get("accuracy", 0)
            diff = e_acc - b_acc
            pct_improvement = (diff / b_acc * 100) if b_acc > 0 else 0

            summary[benchmark_name] = {
                "baseline_accuracy": round(b_acc, 4),
                "enhanced_accuracy": round(e_acc, 4),
                "absolute_improvement": round(diff, 4),
                "relative_improvement_pct": round(pct_improvement, 2),
            }

        return summary


class EnhancedLLMClient:
    """Wrapper that uses LLMEnhancer as an LLM client interface."""

    def __init__(self, enhancer: Any):
        self._enhancer = enhancer
        self._last_result: dict[str, Any] = {}

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send chat message through enhancer."""
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        options = None
        if "options" in user_message.lower() or chr(65) in user_message:
            import re
            opt_matches = re.findall(r"[A-D]\.\s*(.+?)(?=[A-D]\.|$)", user_message, re.DOTALL)
            if opt_matches:
                options = [opt.strip() for opt in opt_matches]

        result = self._enhancer.enhance(
            question=user_message,
            options=options,
        )
        self._last_result = result

        enhanced_answer = result.get("enhanced_answer", result.get("baseline_answer", ""))

        return LLMResponse(
            content=enhanced_answer,
            tool_calls=[],
            usage=TokenUsage(),
            finish_reason="stop",
        )
