"""Tests for LLM enhancer module."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from zhushou.llm.base import LLMResponse, TokenUsage
from zhushou.llm_enhancer import (
    EnhancementConfig,
    LLMEnhancer,
    PromptStrategy,
    PromptLibrary,
    SelfCritique,
    ConstitutionalCritique,
    SelfConsistencyVoter,
    MajorityVotingEnsemble,
    ReasoningEnsemble,
    MMLU,
    GSM8K,
    Hellaswag,
    BenchmarkRunner,
    ComparisonRunner,
    build_few_shot_prompt,
)


class TestPromptLibrary:
    """Tests for prompt templates."""

    def test_get_zero_shot(self):
        template = PromptLibrary.get_zero_shot()
        assert template.system != ""
        messages = template.render(question="What is 2+2?")
        assert len(messages) >= 1
        assert messages[-1]["role"] == "user"

    def test_get_chain_of_thought(self):
        template = PromptLibrary.get_chain_of_thought()
        messages = template.render(question="What is 2+2?")
        assert any("step" in msg.get("content", "").lower() for msg in messages)

    def test_get_mcq(self):
        options = ["A", "B", "C", "D"]
        template = PromptLibrary.get_mcq(options)
        messages = template.render(question="What is 2+2?", options=options)
        content = messages[-1]["content"]
        for i, opt in enumerate(options):
            assert opt in content


class TestBuildFewShotPrompt:
    """Tests for few-shot prompt building."""

    def test_zero_shot(self):
        messages = build_few_shot_prompt("What is 2+2?", PromptStrategy.ZERO_SHOT)
        assert len(messages) >= 1
        assert messages[-1]["role"] == "user"

    def test_cot_strategy(self):
        messages = build_few_shot_prompt("What is 2+2?", PromptStrategy.CHAIN_OF_THOUGHT)
        assert len(messages) >= 1
        assert "step" in messages[-1]["content"].lower()

    def test_self_critique_strategy(self):
        messages = build_few_shot_prompt("What is 2+2?", PromptStrategy.SELF_CRITIQUE)
        assert len(messages) >= 1


class TestEnhancementConfig:
    """Tests for enhancement configuration."""

    def test_default_config(self):
        config = EnhancementConfig()
        assert config.use_cot is False
        assert config.use_self_consistency is False
        assert config.n_samples == 5

    def test_enabled_strategies(self):
        config = EnhancementConfig(
            use_cot=True,
            use_self_consistency=True,
            use_constitutional=True,
        )
        strategies = config.get_enabled_strategies()
        assert "chain_of_thought" in strategies
        assert "self_consistency" in strategies
        assert "constitutional" in strategies


class TestLLMEnhancer:
    """Tests for the main enhancer class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="The answer is B",
            tool_calls=[],
            usage=TokenUsage(10, 20, 30),
            finish_reason="stop",
        )
        return client

    def test_enhance_zero_shot(self, mock_client):
        """Test basic enhancement without techniques."""
        config = EnhancementConfig()
        enhancer = LLMEnhancer(mock_client, config)
        result = enhancer.enhance("What is 2+2?")

        assert result["question"] == "What is 2+2?"
        assert result["baseline_answer"] == "The answer is B"
        assert len(result["techniques_used"]) == 0

    def test_enhance_with_cot(self, mock_client):
        """Test enhancement with chain-of-thought."""
        config = EnhancementConfig(use_cot=True, use_self_consistency=True, n_samples=3)
        enhancer = LLMEnhancer(mock_client, config)

        with patch.object(enhancer._self_consistency, 'vote') as mock_vote:
            mock_vote.return_value = MagicMock(
                winner="B",
                confidence=0.8,
                votes=[2, 1, 0, 0],
                reasoning="Consistent answer",
            )
            result = enhancer.enhance("What is 2+2?", options=["A", "B", "C", "D"])

        assert "self_consistency" in result["techniques_used"]
        assert result["confidence"] == 0.8

    def test_enhance_batch(self, mock_client):
        """Test batch enhancement."""
        config = EnhancementConfig()
        enhancer = LLMEnhancer(mock_client, config)

        questions = [
            {"question": "What is 2+2?"},
            {"question": "What is 3+3?"},
        ]
        results = enhancer.enhance_batch(questions)

        assert len(results) == 2
        assert all("baseline_answer" in r for r in results)


class TestSelfCritique:
    """Tests for self-critique mechanism."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="No revisions needed. The answer is correct.",
            tool_calls=[],
            usage=TokenUsage(),
            finish_reason="stop",
        )
        return client

    def test_critique_no_issues(self, mock_client):
        """Test critique when no issues found."""
        critique = SelfCritique(mock_client)
        result = critique.critique("What is 2+2?", "The answer is 4.")

        assert result.original_response == "The answer is 4."
        assert result.was_revised is False

    def test_critique_with_revision(self, mock_client):
        """Test critique when revision is needed."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="The answer should be 5.",
            tool_calls=[],
            usage=TokenUsage(),
            finish_reason="stop",
        )
        critique = SelfCritique(client)
        result = critique.critique("What is 2+2?", "The answer is 4.")

        assert result.was_revised is True


class TestSelfConsistencyVoter:
    """Tests for self-consistency voting."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="The answer is A.",
            tool_calls=[],
            usage=TokenUsage(),
            finish_reason="stop",
        )
        return client

    def test_vote_with_options(self, mock_client):
        """Test voting with multiple choice options."""
        voter = SelfConsistencyVoter(mock_client)
        result = voter.vote(
            question="What is 2+2?",
            options=["A. 3", "B. 4", "C. 5"],
            n_samples=3,
            use_cot=False,
        )

        assert result.winner != ""
        assert 0 <= result.confidence <= 1

    def test_vote_without_options(self, mock_client):
        """Test voting without options (free response)."""
        voter = SelfConsistencyVoter(mock_client)
        result = voter.vote(
            question="What is 2+2?",
            n_samples=3,
            use_cot=False,
        )

        assert result.winner != ""


class TestMajorityVotingEnsemble:
    """Tests for majority voting ensemble."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="The answer is B.",
            tool_calls=[],
            usage=TokenUsage(),
            finish_reason="stop",
        )
        return client

    def test_majority_vote(self, mock_client):
        """Test majority voting."""
        voter = MajorityVotingEnsemble(mock_client)
        result = voter.vote(
            question="What is 2+2?",
            options=["A. 3", "B. 4", "C. 5"],
            n_samples=3,
        )

        assert result.winner != ""
        assert len(result.votes) == 3


class TestReasoningEnsemble:
    """Tests for reasoning ensemble."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="Step by step: 2+2=4. Answer: B",
            tool_calls=[],
            usage=TokenUsage(),
            finish_reason="stop",
        )
        return client

    def test_reasoning_ensemble(self, mock_client):
        """Test reasoning ensemble."""
        ensemble = ReasoningEnsemble(mock_client)
        result = ensemble.vote(
            question="What is 2+2?",
            options=["A. 3", "B. 4", "C. 5"],
        )

        assert result.winner != ""


class TestBenchmarkDatasets:
    """Tests for benchmark datasets."""

    def test_mmlu_name(self):
        dataset = MMLU()
        assert "mmlu" in dataset.name

    def test_gsm8k_name(self):
        dataset = GSM8K()
        assert dataset.name == "gsm8k"

    def test_hellaswag_name(self):
        dataset = Hellaswag()
        assert dataset.name == "hellaswag"

    def test_mmlu_sample(self):
        dataset = MMLU()
        samples = dataset.sample(3, seed=42)
        assert len(samples) <= 3

    def test_gsm8k_fallback_data(self):
        dataset = GSM8K()
        data = dataset.load()
        assert len(data) > 0
        assert "question" in data[0]


class TestBenchmarkRunner:
    """Tests for benchmark runner."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="B",
            tool_calls=[],
            usage=TokenUsage(10, 5, 15),
            finish_reason="stop",
        )
        return client

    def test_run_mmlu_benchmark(self, mock_client):
        """Test running MMLU benchmark."""
        runner = BenchmarkRunner(mock_client, max_samples=5)
        dataset = MMLU()
        result = runner.run(dataset, prompt_strategy="zero_shot")

        assert result.benchmark_name == dataset.name
        assert result.total_samples == 5

    def test_run_gsm8k_benchmark(self, mock_client):
        """Test running GSM8K benchmark."""
        runner = BenchmarkRunner(mock_client, max_samples=5)
        dataset = GSM8K()
        result = runner.run(dataset, prompt_strategy="cot")

        assert result.benchmark_name == dataset.name


class TestComparisonRunner:
    """Tests for comparison runner."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.chat.return_value = LLMResponse(
            content="The answer is B",
            tool_calls=[],
            usage=TokenUsage(10, 5, 15),
            finish_reason="stop",
        )
        return client

    def test_run_comparison(self, mock_client):
        """Test running comparison."""
        runner = ComparisonRunner(mock_client, model_name="test-model")
        report = runner.run_comparison(
            benchmarks=["mmlu"],
            max_samples=5,
        )

        assert report.model_name == "test-model"
        assert "mmlu" in report.benchmarks_tested
        assert "mmlu" in report.baseline_results
        assert "mmlu" in report.enhanced_results

    def test_improvement_calculation(self, mock_client):
        """Test improvement calculation."""
        runner = ComparisonRunner(mock_client, model_name="test")
        baseline = {"test": {"accuracy": 0.5}}
        enhanced = {"test": {"accuracy": 0.7}}

        improvement = runner._calculate_improvement(baseline, enhanced)

        assert improvement["test"]["baseline_accuracy"] == 0.5
        assert improvement["test"]["enhanced_accuracy"] == 0.7
        assert improvement["test"]["absolute_improvement"] == 0.2
