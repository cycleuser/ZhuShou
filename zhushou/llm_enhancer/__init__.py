"""LLM Enhancer - Weak model enhancement framework."""

from __future__ import annotations

__version__ = "1.0.0"

from .enhancer import LLMEnhancer, EnhancementConfig
from .benchmarks import BenchmarkRunner, BenchmarkResult, MMLU, GSM8K, Hellaswag, TruthfulQA, ARC, BenchmarkDataset
from .comparison import ComparisonRunner, ComparisonReport
from .critique import SelfCritique, ConstitutionalCritique, EnsembleCritique, CritiqueResult
from .prompts import PromptStrategy, PromptTemplate, PromptLibrary, build_few_shot_prompt
from .voting import SelfConsistencyVoter, MajorityVotingEnsemble, ReasoningEnsemble, VoteResult

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
