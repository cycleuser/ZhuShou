"""CLI for running LLM enhancer benchmarks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zhushou.llm.factory import LLMClientFactory
from zhushou.llm_enhancer import (
    LLMEnhancer,
    EnhancementConfig,
    BenchmarkRunner,
    ComparisonRunner,
    MMLU,
    GSM8K,
    Hellaswag,
    TruthfulQA,
    ARC,
)


def run_single_benchmark(
    client: Any,
    benchmark_name: str,
    strategy: str = "zero_shot",
    max_samples: int = 30,
) -> dict[str, Any]:
    """Run a single benchmark."""
    benchmark_classes = {
        "mmlu": MMLU,
        "gsm8k": GSM8K,
        "hellaswag": Hellaswag,
        "truthfulqa": TruthfulQA,
        "arc": ARC,
    }

    if benchmark_name not in benchmark_classes:
        return {"error": f"Unknown benchmark: {benchmark_name}"}

    dataset = benchmark_classes[benchmark_name]()
    runner = BenchmarkRunner(llm_client=client, max_samples=max_samples)
    result = runner.run(dataset=dataset, prompt_strategy=strategy)
    return result.to_dict()


def run_comparison(
    client: Any,
    model_name: str,
    benchmarks: list[str],
    max_samples: int = 30,
    enhanced_config: EnhancementConfig | None = None,
) -> dict[str, Any]:
    """Run comparison between baseline and enhanced."""
    runner = ComparisonRunner(llm_client=client, model_name=model_name)
    report = runner.run_comparison(
        benchmarks=benchmarks,
        max_samples=max_samples,
        enhanced_config=enhanced_config,
    )
    return report.to_dict()


def main():
    parser = argparse.ArgumentParser(
        prog="llm-enhancer",
        description="LLM Enhancer - Weak model performance boosting framework",
    )

    parser.add_argument("-V", "--version", action="version", version="llm-enhancer 1.0.0")
    parser.add_argument("--provider", default="ollama", help="LLM provider")
    parser.add_argument("--model", default="huihui_ai/lfm2.5-abliterated:latest", help="Model name")
    parser.add_argument("--base-url", help="Custom base URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run single benchmark")
    benchmark_parser.add_argument("benchmark", choices=["mmlu", "gsm8k", "hellaswag", "truthfulqa", "arc"])
    benchmark_parser.add_argument("--strategy", default="zero_shot", choices=["zero_shot", "cot", "few_shot_cot"])
    benchmark_parser.add_argument("--samples", type=int, default=30, help="Max samples to test")

    compare_parser = subparsers.add_parser("compare", help="Compare baseline vs enhanced")
    compare_parser.add_argument("--benchmarks", nargs="+", default=["mmlu", "gsm8k"], help="Benchmarks to run")
    compare_parser.add_argument("--samples", type=int, default=30, help="Max samples per benchmark")
    compare_parser.add_argument("--enhanced", action="store_true", help="Use enhancement techniques")

    enhance_parser = subparsers.add_parser("enhance", help="Enhance a single question")
    enhance_parser.add_argument("question", help="Question to enhance")
    enhance_parser.add_argument("--options", nargs="*", help="MCQ options")

    args = parser.parse_args()

    client_kwargs = {"provider": args.provider, "model": args.model}
    if args.base_url:
        client_kwargs["base_url"] = args.base_url

    try:
        client = LLMClientFactory.create_client(**client_kwargs)
    except Exception as e:
        print(f"Error creating client: {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "benchmark":
        result = run_single_benchmark(
            client=client,
            benchmark_name=args.benchmark,
            strategy=args.strategy,
            max_samples=args.samples,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== Benchmark: {args.benchmark.upper()} ===")
            print(f"Strategy: {args.strategy}")
            print(f"Samples: {result.get('total', 0)}")
            print(f"Correct: {result.get('correct', 0)}")
            print(f"Accuracy: {result.get('accuracy', 0):.2%}")
            print(f"Avg Latency: {result.get('avg_latency', 0):.2f}s")

    elif args.command == "compare":
        enhanced_config = None
        if args.enhanced:
            enhanced_config = EnhancementConfig(
                use_cot=True,
                use_self_consistency=True,
                use_constitutional=True,
                n_samples=5,
            )

        result = run_comparison(
            client=client,
            model_name=args.model,
            benchmarks=args.benchmarks,
            max_samples=args.samples,
            enhanced_config=enhanced_config,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== Comparison Report: {args.model} ===")
            print(f"\nImprovement Summary:")
            for benchmark, stats in result.get("improvement", {}).items():
                print(f"\n{benchmark.upper()}:")
                print(f"  Baseline: {stats.get('baseline_accuracy', 0):.2%}")
                print(f"  Enhanced: {stats.get('enhanced_accuracy', 0):.2%}")
                print(f"  Improvement: +{stats.get('absolute_improvement', 0):.2%} ({stats.get('relative_improvement_pct', 0):.1f}%)")

    elif args.command == "enhance":
        config = EnhancementConfig(
            use_cot=True,
            use_self_consistency=True,
            use_constitutional=True,
        )
        enhancer = LLMEnhancer(client, config)
        result = enhancer.enhance(args.question, args.options)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== Enhancement Result ===")
            print(f"\nQuestion: {result['question']}")
            print(f"\nBaseline Answer: {result.get('baseline_answer', 'N/A')}")
            print(f"\nEnhanced Answer: {result.get('enhanced_answer', 'N/A')}")
            print(f"\nTechniques Used: {', '.join(result.get('techniques_used', []))}")
            print(f"Confidence: {result.get('confidence', 0):.2f}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
