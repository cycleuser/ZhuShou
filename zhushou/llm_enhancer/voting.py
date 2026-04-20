"""Voting and ensemble mechanisms for weak model enhancement."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from zhushou.llm.base import LLMResponse


@dataclass
class VoteResult:
    """Result of a voting operation."""

    candidates: list[str]
    votes: list[int]
    winner: str
    confidence: float
    reasoning: str


class SelfConsistencyVoter:
    """Self-consistency voting - sample multiple times and pick most consistent answer.

    Reference: Wang et al. "Self-Consistency Improves Chain of Thought Reasoning"
    """

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def vote(
        self,
        question: str,
        options: list[str] | None = None,
        n_samples: int = 5,
        temperature: float = 0.7,
        use_cot: bool = True,
    ) -> VoteResult:
        """Run self-consistency voting."""
        samples: list[dict[str, Any]] = []

        for i in range(n_samples):
            messages = self._build_prompt(question, options, use_cot)
            try:
                response = self._client.chat(messages=messages, temperature=temperature)
                answer = self._parse_answer(response.content, options)
                samples.append({
                    "response": response.content,
                    "answer": answer,
                    "index": i,
                })
            except Exception as e:
                samples.append({
                    "response": str(e),
                    "answer": None,
                    "index": i,
                })

        valid_answers = [s["answer"] for s in samples if s["answer"] is not None]

        if not valid_answers:
            return VoteResult(
                candidates=[],
                votes=[],
                winner="",
                confidence=0.0,
                reasoning="No valid answers obtained",
            )

        if options:
            answer_counts = Counter(valid_answers)
            winner_idx = answer_counts.most_common(1)[0][0]
            winner = options[winner_idx] if isinstance(winner_idx, int) else str(winner_idx)
            confidence = answer_counts[winner_idx] / len(valid_answers)

            vote_list = [0] * len(options)
            for ans in valid_answers:
                if isinstance(ans, int) and 0 <= ans < len(options):
                    vote_list[ans] += 1

            return VoteResult(
                candidates=options,
                votes=vote_list,
                winner=winner,
                confidence=confidence,
                reasoning=f"Won by {answer_counts[winner_idx]} out of {len(valid_answers)} samples",
            )
        else:
            answer_counts = Counter(valid_answers)
            winner = answer_counts.most_common(1)[0][0]
            confidence = answer_counts[winner] / len(valid_answers)

            return VoteResult(
                candidates=list(answer_counts.keys()),
                votes=list(answer_counts.values()),
                winner=str(winner),
                confidence=confidence,
                reasoning=f"Won by {answer_counts[winner]} out of {len(valid_answers)} samples",
            )

    def _build_prompt(
        self,
        question: str,
        options: list[str] | None,
        use_cot: bool,
    ) -> list[dict[str, str]]:
        """Build prompt for a single sample."""
        if use_cot:
            if options:
                options_text = "\n".join(f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options))
                content = f"{question}\n\nOptions:\n{options_text}\n\nLet's think step by step:"
            else:
                content = f"{question}\n\nLet's think step by step:"
        else:
            if options:
                options_text = "\n".join(f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options))
                content = f"{question}\n\nOptions:\n{options_text}"
            else:
                content = question

        return [{"role": "user", "content": content}]

    def _parse_answer(
        self,
        content: str,
        options: list[str] | None,
    ) -> int | str | None:
        """Parse answer from response content."""
        content = content.strip()

        if options:
            content_upper = content.upper()
            for i in range(len(options)):
                letter = chr(65 + i)
                if f"{letter}." in content_upper or content_upper.startswith(letter):
                    return i

            for i, opt in enumerate(options):
                if opt[:20].lower() in content.lower():
                    return i

        import re
        numbers = re.findall(r"(?:answer|result)[:\s]*(\d+)", content, re.IGNORECASE)
        if numbers:
            return numbers[-1]

        return content[:100] if content else None


class MajorityVotingEnsemble:
    """Simple majority voting across multiple generation attempts."""

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def vote(
        self,
        question: str,
        options: list[str] | None = None,
        n_samples: int = 3,
        temperature: float = 0.5,
    ) -> VoteResult:
        """Run majority voting."""
        samples: list[str] = []

        for _ in range(n_samples):
            messages = [{"role": "user", "content": question}]
            try:
                response = self._client.chat(messages=messages, temperature=temperature)
                samples.append(response.content)
            except Exception:
                samples.append("")

        if options:
            answer_counts = Counter()
            for sample in samples:
                answer = self._parse_answer(sample, options)
                if answer is not None:
                    answer_counts[answer] += 1

            if not answer_counts:
                return VoteResult(
                    candidates=options,
                    votes=[0] * len(options),
                    winner=options[0],
                    confidence=0.0,
                    reasoning="No parseable answers",
                )

            winner_idx = answer_counts.most_common(1)[0][0]
            winner = options[winner_idx]
            confidence = answer_counts[winner_idx] / n_samples

            vote_list = [0] * len(options)
            for ans, count in answer_counts.items():
                if isinstance(ans, int) and 0 <= ans < len(options):
                    vote_list[ans] = count

            return VoteResult(
                candidates=options,
                votes=vote_list,
                winner=winner,
                confidence=confidence,
                reasoning=f"Won by {answer_counts[winner_idx]} out of {n_samples}",
            )
        else:
            answer_counts = Counter(samples)
            winner = answer_counts.most_common(1)[0][0]
            confidence = answer_counts[winner] / n_samples

            return VoteResult(
                candidates=list(answer_counts.keys()),
                votes=list(answer_counts.values()),
                winner=winner,
                confidence=confidence,
                reasoning=f"Won by {answer_counts[winner]} out of {n_samples}",
            )

    def _parse_answer(
        self,
        content: str,
        options: list[str],
    ) -> int | None:
        """Parse answer from content."""
        content_upper = content.upper()
        for i in range(len(options)):
            letter = chr(65 + i)
            if f"{letter}." in content_upper or content_upper.startswith(letter):
                return i

            if options[i][:20].lower() in content.lower():
                return i

        return None


class ReasoningEnsemble:
    """Ensemble specifically designed for reasoning tasks."""

    REASONING_STRATEGIES = [
        ("direct", "Answer directly and concisely."),
        ("step_by_step", "Let's think step by step."),
        ("alternatives", "Consider multiple perspectives and explain the most likely answer."),
        ("verification", "Think through the answer and verify it makes sense."),
    ]

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def vote(
        self,
        question: str,
        options: list[str] | None = None,
        temperature: float = 0.4,
    ) -> VoteResult:
        """Run reasoning ensemble using different prompting strategies."""
        results: list[dict[str, Any]] = []

        for strategy_name, strategy_hint in self.REASONING_STRATEGIES:
            messages = self._build_prompt(question, options, strategy_hint)
            try:
                response = self._client.chat(messages=messages, temperature=temperature)
                answer = self._parse_answer(response.content, options)
                results.append({
                    "strategy": strategy_name,
                    "response": response.content,
                    "answer": answer,
                })
            except Exception as e:
                results.append({
                    "strategy": strategy_name,
                    "response": str(e),
                    "answer": None,
                })

        valid_answers = [r["answer"] for r in results if r["answer"] is not None]

        if not valid_answers:
            return VoteResult(
                candidates=[],
                votes=[],
                winner="",
                confidence=0.0,
                reasoning="No valid answers",
            )

        if options:
            answer_counts = Counter(valid_answers)
            winner_idx = answer_counts.most_common(1)[0][0]
            winner = options[winner_idx] if isinstance(winner_idx, int) else str(winner_idx)
            confidence = answer_counts[winner_idx] / len(valid_answers)

            vote_list = [0] * len(options)
            for ans in valid_answers:
                if isinstance(ans, int) and 0 <= ans < len(options):
                    vote_list[ans] += 1

            return VoteResult(
                candidates=options,
                votes=vote_list,
                winner=winner,
                confidence=confidence,
                reasoning=f"Strategy ensemble: {len(valid_answers)}/{len(self.REASONING_STRATEGIES)} agreed",
            )
        else:
            answer_counts = Counter(valid_answers)
            winner = answer_counts.most_common(1)[0][0]
            confidence = answer_counts[winner] / len(valid_answers)

            return VoteResult(
                candidates=list(answer_counts.keys()),
                votes=list(answer_counts.values()),
                winner=str(winner),
                confidence=confidence,
                reasoning=f"Strategy ensemble: {len(valid_answers)}/{len(self.REASONING_STRATEGIES)} agreed",
            )

    def _build_prompt(
        self,
        question: str,
        options: list[str] | None,
        strategy_hint: str,
    ) -> list[dict[str, str]]:
        """Build prompt with specific reasoning strategy."""
        if options:
            options_text = "\n".join(f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options))
            content = f"{question}\n\nOptions:\n{options_text}\n\n{strategy_hint}"
        else:
            content = f"{question}\n\n{strategy_hint}"

        return [{"role": "user", "content": content}]

    def _parse_answer(
        self,
        content: str,
        options: list[str] | None,
    ) -> int | str | None:
        """Parse answer from content."""
        if options:
            content_upper = content.upper()
            for i in range(len(options)):
                letter = chr(65 + i)
                if f"{letter}." in content_upper or content_upper.startswith(letter):
                    return i

            for i, opt in enumerate(options):
                if opt[:20].lower() in content.lower():
                    return i

            import re
            match = re.search(r"\b([A-D])\b", content_upper)
            if match:
                return ord(match.group(1)) - ord("A")

        return content.strip() if content else None
