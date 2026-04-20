#!/usr/bin/env python3
"""Interactive testing script for comparing enhancement strategies.

Usage:
    python interactive_test.py                    # Interactive mode
    python interactive_test.py --question "..."   # Single question mode
    python interactive_test.py --batch            # Batch testing mode
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from zhushou.llm.factory import LLMClientFactory
from zhushou.llm_enhancer import (
    EnhancementConfig,
    LLMEnhancer,
    MMLU,
    GSM8K,
    BenchmarkRunner,
)
from zhushou.llm_enhancer.advanced_strategies import (
    TreeOfThoughts,
    ReActPrompting,
    Reflexion,
    StepBackPrompting,
    LeastToMost,
    GraphOfThoughts,
)


def create_client(provider: str, model: str, base_url: str | None = None) -> object:
    """Create LLM client."""
    kwargs = {"provider": provider, "model": model}
    if base_url:
        kwargs["base_url"] = base_url
    return LLMClientFactory.create_client(**kwargs)


def test_single_question(client: object, question: str, options: list[str] | None = None):
    """Test a single question with all strategies."""
    print("\n" + "=" * 80)
    print(f"QUESTION: {question}")
    if options:
        print(f"OPTIONS: {', '.join(options)}")
    print("=" * 80)

    results = {}

    strategies = [
        ("Zero-Shot (Baseline)", EnhancementConfig()),
        ("Chain-of-Thought", EnhancementConfig(use_cot=True)),
        ("Self-Consistency (5 samples)", EnhancementConfig(use_cot=True, use_self_consistency=True, n_samples=5)),
        ("Full Enhancement", EnhancementConfig(use_cot=True, use_self_consistency=True, use_constitutional=True, n_samples=5)),
    ]

    for name, config in strategies:
        print(f"\n{'─' * 60}")
        print(f"Testing: {name}")
        print(f"{'─' * 60}")

        start = time.time()
        enhancer = LLMEnhancer(client, config)
        result = enhancer.enhance(question, options)
        elapsed = time.time() - start

        answer = result.get("enhanced_answer", result.get("baseline_answer", ""))
        print(f"Answer: {answer[:200]}...")
        print(f"Time: {elapsed:.2f}s")
        print(f"Techniques: {', '.join(result.get('techniques_used', []))}")

        results[name] = {"answer": answer, "time": elapsed, "techniques": result.get("techniques_used", [])}

    return results


def test_advanced_strategies(client: object, question: str):
    """Test advanced prompting strategies."""
    print("\n" + "=" * 80)
    print(f"ADVANCED STRATEGIES TEST: {question}")
    print("=" * 80)

    results = {}

    strategies = [
        ("Tree of Thoughts", TreeOfThoughts(client, max_depth=2, branching_factor=2)),
        ("ReAct", ReActPrompting(client, max_steps=3)),
        ("Reflexion", Reflexion(client, max_trials=2)),
        ("Step-Back", StepBackPrompting(client)),
        ("Least-to-Most", LeastToMost(client)),
        ("Graph of Thoughts", GraphOfThoughts(client, max_iterations=2)),
    ]

    for name, strategy in strategies:
        print(f"\n{'─' * 60}")
        print(f"Testing: {name}")
        print(f"{'─' * 60}")

        start = time.time()
        try:
            answer = strategy.solve(question)
            elapsed = time.time() - start
            print(f"Answer: {answer[:200]}...")
            print(f"Time: {elapsed:.2f}s")
            results[name] = {"answer": answer, "time": elapsed}
        except Exception as e:
            print(f"Error: {e}")
            results[name] = {"answer": f"Error: {e}", "time": 0}

    return results


def run_benchmark_comparison(client: object, benchmark_name: str, max_samples: int = 10):
    """Run benchmark comparison."""
    print(f"\n{'=' * 80}")
    print(f"BENCHMARK: {benchmark_name.upper()}")
    print(f"{'=' * 80}")

    benchmark_classes = {
        "mmlu": MMLU,
        "gsm8k": GSM8K,
    }

    if benchmark_name not in benchmark_classes:
        print(f"Unknown benchmark: {benchmark_name}")
        return

    dataset = benchmark_classes[benchmark_name]()
    runner = BenchmarkRunner(client, max_samples=max_samples)

    for strategy in ["zero_shot", "cot"]:
        print(f"\n{'─' * 60}")
        print(f"Strategy: {strategy}")
        print(f"{'─' * 60}")

        result = runner.run(dataset, prompt_strategy=strategy)
        print(f"Accuracy: {result.accuracy:.2%}")
        print(f"Correct: {result.correct}/{result.total_samples}")
        print(f"Avg Latency: {result.avg_latency:.2f}s")


def interactive_mode(client: object):
    """Interactive mode for testing questions."""
    print("\n" + "=" * 80)
    print("LLM ENHANCER - INTERACTIVE TESTING")
    print("=" * 80)
    print("\nCommands:")
    print("  /baseline   - Test with baseline (zero-shot)")
    print("  /enhanced   - Test with full enhancement")
    print("  /advanced   - Test with advanced strategies")
    print("  /benchmark  - Run benchmark comparison")
    print("  /quit       - Exit")
    print("  /help       - Show this help")
    print("\nOr just type your question to test all strategies.\n")

    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue

        if question.startswith("/"):
            command = question.lower()
            if command == "/quit" or command == "/exit":
                print("Goodbye!")
                break
            elif command == "/help":
                print("Commands: /baseline, /enhanced, /advanced, /benchmark, /quit")
            elif command == "/baseline":
                q = input("Enter question: ").strip()
                if q:
                    test_single_question(client, q)
            elif command == "/enhanced":
                q = input("Enter question: ").strip()
                if q:
                    test_single_question(client, q)
            elif command == "/advanced":
                q = input("Enter question: ").strip()
                if q:
                    test_advanced_strategies(client, q)
            elif command == "/benchmark":
                bench = input("Benchmark (mmlu/gsm8k): ").strip()
                if bench:
                    run_benchmark_comparison(client, bench)
            continue

        test_single_question(client, question)
        test_advanced_strategies(client, question)


def main():
    parser = argparse.ArgumentParser(description="LLM Enhancer Interactive Testing")
    parser.add_argument("--provider", default="ollama", help="LLM provider")
    parser.add_argument("--model", default="huihui_ai/lfm2.5-abliterated:latest", help="Model name")
    parser.add_argument("--base-url", help="Custom base URL")
    parser.add_argument("--question", help="Single question to test")
    parser.add_argument("--options", nargs="*", help="MCQ options")
    parser.add_argument("--benchmark", help="Run benchmark (mmlu/gsm8k)")
    parser.add_argument("--samples", type=int, default=10, help="Samples for benchmark")
    parser.add_argument("--advanced", action="store_true", help="Test advanced strategies")
    parser.add_argument("--output", help="Save results to file")

    args = parser.parse_args()

    print("Creating LLM client...")
    client = create_client(args.provider, args.model, args.base_url)
    print(f"Connected to {args.provider}/{args.model}\n")

    all_results = {}

    if args.question:
        all_results["basic"] = test_single_question(client, args.question, args.options)
        if args.advanced:
            all_results["advanced"] = test_advanced_strategies(client, args.question)

    elif args.benchmark:
        run_benchmark_comparison(client, args.benchmark, args.samples)

    else:
        interactive_mode(client)

    if args.output and all_results:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
