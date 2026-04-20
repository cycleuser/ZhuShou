"""Core LLM enhancer module that orchestrates all enhancement techniques."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from .benchmarks import BenchmarkRunner, BenchmarkResult, MMLU, GSM8K, Hellaswag, TruthfulQA, ARC, BenchmarkDataset
from .comparison import ComparisonRunner, ComparisonReport
from .critique import SelfCritique, ConstitutionalCritique, EnsembleCritique, CritiqueResult
from .prompts import (
    PromptStrategy,
    PromptTemplate,
    PromptLibrary,
    build_few_shot_prompt,
    COT_EXAMPLES_MATH,
    COT_EXAMPLES_COMMON,
    COT_EXAMPLES_MCQ,
)
from .voting import (
    SelfConsistencyVoter,
    MajorityVotingEnsemble,
    ReasoningEnsemble,
    VoteResult,
)


@dataclass
class EnhancementConfig:
    """Configuration for enhancement techniques."""

    use_cot: bool = False
    use_few_shot: bool = False
    use_self_critique: bool = False
    use_constitutional: bool = False
    use_self_consistency: bool = False
    use_majority_voting: bool = False
    use_reasoning_ensemble: bool = False
    n_samples: int = 5
    temperature: float = 0.3
    critique_temperature: float = 0.4
    voting_temperature: float = 0.7

    def get_enabled_strategies(self) -> list[str]:
        """Get list of enabled strategies."""
        strategies = []
        if self.use_cot:
            strategies.append("chain_of_thought")
        if self.use_few_shot:
            strategies.append("few_shot")
        if self.use_self_critique:
            strategies.append("self_critique")
        if self.use_constitutional:
            strategies.append("constitutional")
        if self.use_self_consistency:
            strategies.append("self_consistency")
        if self.use_majority_voting:
            strategies.append("majority_voting")
        if self.use_reasoning_ensemble:
            strategies.append("reasoning_ensemble")
        return strategies


__all__ = [
    "LLMEnhancer",
    "EnhancementConfig",
    "BenchmarkRunner",
    "BenchmarkResult",
    "BenchmarkDataset",
    "ComparisonRunner",
    "ComparisonReport",
    "SelfCritique",
    "ConstitutionalCritique",
    "EnsembleCritique",
    "CritiqueResult",
    "PromptStrategy",
    "PromptTemplate",
    "PromptLibrary",
    "SelfConsistencyVoter",
    "MajorityVotingEnsemble",
    "ReasoningEnsemble",
    "VoteResult",
    "MMLU",
    "GSM8K",
    "Hellaswag",
    "TruthfulQA",
    "ARC",
    "build_few_shot_prompt",
]


class LLMEnhancer:
    """Main enhancer class for improving weak model performance.

    This class coordinates various enhancement techniques:
    - Chain-of-Thought (CoT) prompting
    - Few-shot learning
    - Self-consistency voting
    - Self-critique and revision
    - Constitutional AI-style critique
    - Reasoning ensemble

    Usage:
        config = EnhancementConfig(
            use_cot=True,
            use_self_consistency=True,
            use_constitutional=True,
            n_samples=5,
        )
        enhancer = LLMEnhancer(llm_client, config)
        result = enhancer.enhance("What is 2+2?", options=["3", "4", "5", "6"])
    """

    def __init__(self, llm_client: Any, config: EnhancementConfig | None = None):
        """Initialize enhancer with LLM client and configuration.

        Args:
            llm_client: An LLM client with a chat() method.
            config: Enhancement configuration. Uses defaults if None.
        """
        self._client = llm_client
        self.config = config or EnhancementConfig()

        self._critique = SelfCritique(llm_client)
        self._constitutional = ConstitutionalCritique(llm_client)
        self._ensemble_critique = EnsembleCritique(llm_client)
        self._self_consistency = SelfConsistencyVoter(llm_client)
        self._majority_voting = MajorityVotingEnsemble(llm_client)
        self._reasoning_ensemble = ReasoningEnsemble(llm_client)

    def enhance(
        self,
        question: str,
        options: list[str] | None = None,
    ) -> dict[str, Any]:
        """Enhance a single question and return improved answer.

        Args:
            question: The question to answer.
            options: Optional list of choices for MCQ.

        Returns:
            Dictionary containing:
                - question: Original question
                - options: Options if provided
                - baseline_answer: Direct answer from model
                - enhanced_answer: Final enhanced answer
                - techniques_used: List of techniques applied
                - confidence: Confidence score
                - details: Additional technique-specific results
        """
        result: dict[str, Any] = {
            "question": question,
            "options": options,
            "baseline_answer": None,
            "enhanced_answer": None,
            "techniques_used": [],
            "confidence": 0.0,
            "details": {},
        }

        baseline_messages = [{"role": "user", "content": question}]
        try:
            baseline_response = self._client.chat(
                messages=baseline_messages,
                temperature=self.config.temperature,
            )
            result["baseline_answer"] = baseline_response.content
        except Exception as e:
            result["baseline_error"] = str(e)
            return result

        answer = baseline_response.content
        confidence = 0.5

        if self.config.use_self_consistency:
            result["techniques_used"].append("self_consistency")
            vote_result = self._self_consistency.vote(
                question=question,
                options=options,
                n_samples=self.config.n_samples,
                temperature=self.config.voting_temperature,
                use_cot=self.config.use_cot,
            )
            answer = vote_result.winner
            confidence = max(confidence, vote_result.confidence)
            result["details"]["self_consistency"] = {
                "winner": vote_result.winner,
                "confidence": vote_result.confidence,
                "votes": vote_result.votes,
                "reasoning": vote_result.reasoning,
            }

        if self.config.use_reasoning_ensemble:
            result["techniques_used"].append("reasoning_ensemble")
            vote_result = self._reasoning_ensemble.vote(
                question=question,
                options=options,
                temperature=self.config.voting_temperature,
            )
            answer = vote_result.winner
            confidence = max(confidence, vote_result.confidence)
            result["details"]["reasoning_ensemble"] = {
                "winner": vote_result.winner,
                "confidence": vote_result.confidence,
                "reasoning": vote_result.reasoning,
            }

        if self.config.use_majority_voting:
            result["techniques_used"].append("majority_voting")
            vote_result = self._majority_voting.vote(
                question=question,
                options=options,
                n_samples=self.config.n_samples,
                temperature=self.config.voting_temperature,
            )
            answer = vote_result.winner
            confidence = max(confidence, vote_result.confidence)
            result["details"]["majority_voting"] = {
                "winner": vote_result.winner,
                "confidence": vote_result.confidence,
                "votes": vote_result.votes,
            }

        if self.config.use_constitutional:
            result["techniques_used"].append("constitutional")
            critique_result = self._constitutional.critique(
                question=question,
                response=answer,
                temperature=self.config.critique_temperature,
            )
            result["details"]["constitutional"] = {
                "critique": critique_result.critique,
                "issues_found": critique_result.issues_found,
                "was_revised": critique_result.was_revised,
            }
            if critique_result.revised_response:
                answer = critique_result.revised_response
                confidence = min(confidence + 0.1, 1.0)

        if self.config.use_self_critique:
            result["techniques_used"].append("self_critique")
            critique_result = self._critique.critique(
                question=question,
                response=answer,
                temperature=self.config.critique_temperature,
            )
            result["details"]["self_critique"] = {
                "critique": critique_result.critique,
                "issues_found": critique_result.issues_found,
                "was_revised": critique_result.was_revised,
            }
            if critique_result.revised_response:
                answer = critique_result.revised_response
                confidence = min(confidence + 0.1, 1.0)

        result["enhanced_answer"] = answer
        result["confidence"] = confidence

        return result

    def enhance_batch(
        self,
        questions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enhance a batch of questions.

        Args:
            questions: List of dicts with 'question' and optional 'options'.

        Returns:
            List of enhancement results.
        """
        results = []
        for item in questions:
            result = self.enhance(
                question=item.get("question", ""),
                options=item.get("options"),
            )
            results.append(result)
        return results

    def stream_enhance(
        self,
        question: str,
        options: list[str] | None = None,
    ) -> Iterator[str]:
        """Stream the enhanced answer token by token.

        Note: This is a simplified streaming version that generates
        the answer and then streams it. For true streaming with all
        enhancement techniques, use enhance() instead.
        """
        result = self.enhance(question=question, options=options)
        answer = result.get("enhanced_answer", result.get("baseline_answer", ""))
        for token in answer:
            yield token


@dataclass
class EnhancementResult:
    """Container for enhancement result with typed fields."""

    question: str
    options: list[str] | None
    baseline_answer: str
    enhanced_answer: str
    techniques_used: list[str]
    confidence: float
    was_improved: bool
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnhancementResult":
        """Create from dictionary."""
        return cls(
            question=data.get("question", ""),
            options=data.get("options"),
            baseline_answer=data.get("baseline_answer", ""),
            enhanced_answer=data.get("enhanced_answer", ""),
            techniques_used=data.get("techniques_used", []),
            confidence=data.get("confidence", 0.0),
            was_improved=data.get("was_improved", False),
            details=data.get("details", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question": self.question,
            "options": self.options,
            "baseline_answer": self.baseline_answer,
            "enhanced_answer": self.enhanced_answer,
            "techniques_used": self.techniques_used,
            "confidence": self.confidence,
            "was_improved": self.was_improved,
            "details": self.details,
        }
