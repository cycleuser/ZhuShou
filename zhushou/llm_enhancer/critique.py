"""Self-critique and revision mechanisms for weak model enhancement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zhushou.llm.base import LLMResponse


@dataclass
class CritiqueResult:
    """Result of a self-critique operation."""

    original_response: str
    critique: str
    revised_response: str | None
    issues_found: list[str]
    was_revised: bool


class SelfCritique:
    """Self-critique mechanism for improving model responses."""

    CRITIQUE_PROMPT = """You are a critical reviewer. Analyze the following response and identify any issues:

Response: {response}

Question: {question}

Evaluate the response on these criteria:
1. Accuracy - Is the information correct?
2. Relevance - Does it address the question?
3. Completeness - Is it fully addressed?
4. Clarity - Is it clear and understandable?

If you find issues, provide a revised, better response. If no issues, say "No revisions needed"."""

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def critique(
        self,
        question: str,
        response: str,
        temperature: float = 0.3,
    ) -> CritiqueResult:
        """Critique a response and potentially revise it."""
        messages = [
            {"role": "user", "content": self.CRITIQUE_PROMPT.format(
                question=question,
                response=response,
            )},
        ]

        try:
            result = self._client.chat(messages=messages, temperature=temperature)
            critique_text = result.content

            issues = self._extract_issues(critique_text)
            revised = None
            was_revised = False

            if "no revisions needed" not in critique_text.lower() and len(critique_text) < len(response) * 2:
                revised = critique_text
                was_revised = True

            return CritiqueResult(
                original_response=response,
                critique=critique_text,
                revised_response=revised,
                issues_found=issues,
                was_revised=was_revised,
            )
        except Exception as e:
            return CritiqueResult(
                original_response=response,
                critique=f"Error during critique: {e}",
                revised_response=None,
                issues_found=[],
                was_revised=False,
            )

    def _extract_issues(self, critique_text: str) -> list[str]:
        """Extract identified issues from critique text."""
        issues = []
        lower_text = critique_text.lower()

        if "inaccurate" in lower_text or "incorrect" in lower_text:
            issues.append("accuracy")
        if "irrelevant" in lower_text or "off topic" in lower_text:
            issues.append("relevance")
        if "incomplete" in lower_text or "missing" in lower_text:
            issues.append("completeness")
        if "unclear" in lower_text or "confusing" in lower_text:
            issues.append("clarity")

        return issues


class ConstitutionalCritique:
    """Constitutional AI-style critique based on principles."""

    PRINCIPLES = [
        "The assistant should provide accurate, factual information.",
        "The assistant should be helpful and directly address the user's question.",
        "The assistant should avoid harmful, unethical, or dangerous content.",
        "The assistant should be concise and not overly verbose.",
        "The assistant should acknowledge uncertainty when appropriate.",
    ]

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def critique(
        self,
        question: str,
        response: str,
        temperature: float = 0.3,
    ) -> CritiqueResult:
        """Critique using constitutional principles."""
        principles_text = "\n".join(f"{i+1}. {p}" for i, p in enumerate(self.PRINCIPLES))

        messages = [
            {"role": "system", "content": "You are a principle-guided reviewer."},
            {"role": "user", "content": f"""Review the following response against these principles:

Principles:
{principles_text}

Question: {question}

Response: {response}

For each principle, indicate if it is satisfied or violated. If violations exist, provide a corrected response.

Provide your review followed by any corrected version."""},
        ]

        try:
            result = self._client.chat(messages=messages, temperature=temperature)
            critique_text = result.content

            issues = self._extract_issues(critique_text)
            revised = self._extract_revision(critique_text)

            return CritiqueResult(
                original_response=response,
                critique=critique_text,
                revised_response=revised,
                issues_found=issues,
                was_revised=revised is not None,
            )
        except Exception as e:
            return CritiqueResult(
                original_response=response,
                critique=f"Error during critique: {e}",
                revised_response=None,
                issues_found=[],
                was_revised=False,
            )

    def _extract_issues(self, critique_text: str) -> list[str]:
        """Extract violated principles from critique."""
        issues = []
        lower_text = critique_text.lower()
        principle_keywords = ["accuracy", "factual", "helpful", "relevant", "harmful", "dangerous", "concise", "verbose", "uncertainty"]

        for keyword in principle_keywords:
            if keyword in lower_text and ("violat" in lower_text or "fail" in lower_text):
                issues.append(keyword)

        return issues

    def _extract_revision(self, critique_text: str) -> str | None:
        """Extract corrected response if present."""
        markers = ["corrected version:", "revised response:", "corrected:", "revised:"]
        lower_text = critique_text.lower()

        for marker in markers:
            idx = lower_text.find(marker)
            if idx != -1:
                revised = critique_text[idx + len(marker):].strip()
                if len(revised) > 10:
                    return revised

        if "no violations" in lower_text or "all principles" in lower_text:
            return None

        return None


class EnsembleCritique:
    """Critique through ensemble of multiple perspectives."""

    PERSPECTIVES = [
        ("technical", "You are a technical expert. Evaluate the technical accuracy."),
        ("common_sense", "You are a practical person. Evaluate based on common sense."),
        ("detail_oriented", "You are detail-oriented. Check for specific errors or omissions."),
        ("synthesizer", "You synthesize multiple viewpoints. Provide balanced evaluation."),
    ]

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def critique(
        self,
        question: str,
        response: str,
        temperature: float = 0.4,
    ) -> CritiqueResult:
        """Get critique from multiple perspectives and synthesize."""
        perspectives_results = []

        for perspective_name, perspective_prompt in self.PERSPECTIVES:
            messages = [
                {"role": "system", "content": perspective_prompt},
                {"role": "user", "content": f"Question: {question}\n\nResponse: {response}\n\nProvide brief evaluation:"},
            ]
            try:
                result = self._client.chat(messages=messages, temperature=temperature)
                perspectives_results.append({
                    "perspective": perspective_name,
                    "evaluation": result.content,
                })
            except Exception:
                pass

        synthesis_messages = [
            {"role": "system", "content": "You synthesize information from multiple perspectives."},
            {"role": "user", "content": f"""Synthesize the following evaluations and provide a final assessment:

Question: {question}
Original Response: {response}

Evaluations from different perspectives:
{self._format_perspectives(perspectives_results)}

Provide a synthesis and any corrected version if needed."""},
        ]

        try:
            result = self._client.chat(messages=synthesis_messages, temperature=temperature)
            critique_text = result.content
            revised = self._extract_revision(critique_text)

            return CritiqueResult(
                original_response=response,
                critique=critique_text,
                revised_response=revised,
                issues_found=[],
                was_revised=revised is not None,
            )
        except Exception as e:
            return CritiqueResult(
                original_response=response,
                critique=str(e),
                revised_response=None,
                issues_found=[],
                was_revised=False,
            )

    def _format_perspectives(self, results: list[dict[str, str]]) -> str:
        return "\n".join(
            f"- {r['perspective']}: {r['evaluation']}" for r in results
        )

    def _extract_revision(self, text: str) -> str | None:
        markers = ["corrected version:", "revised response:", "final answer:"]
        lower_text = text.lower()
        for marker in markers:
            idx = lower_text.find(marker)
            if idx != -1:
                return text[idx + len(marker):].strip()
        return None
