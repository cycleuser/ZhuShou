"""Prompt engineering strategies for weak model enhancement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PromptStrategy(Enum):
    """Available prompting strategies."""

    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    CHAIN_OF_THOUGHT_FEW_SHOT = "cot_few_shot"
    SELF_CONSISTENCY = "self_consistency"
    SELF_CRITIQUE = "self_critique"
    CONSTITUTIONAL = "constitutional"
    ENSEMBLE_VOTING = "ensemble_voting"


@dataclass
class PromptTemplate:
    """A prompt template with variables."""

    system: str = ""
    user_template: str = ""
    examples: list[dict[str, str]] = field(default_factory=list)

    def render(
        self,
        question: str,
        answer: str | None = None,
        options: list[str] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, str]]:
        """Render the template into a message list."""
        messages = []

        if self.system:
            messages.append({"role": "system", "content": self.system})

        if self.examples:
            for ex in self.examples:
                if "question" in ex:
                    messages.append({"role": "user", "content": ex["question"]})
                if "answer" in ex:
                    messages.append({"role": "assistant", "content": ex["answer"]})

        content = self.user_template.format(
            question=question,
            answer=answer or "",
            options=self._format_options(options) if options else "",
            **kwargs,
        )
        messages.append({"role": "user", "content": content})

        return messages

    def _format_options(self, options: list[str]) -> str:
        if not options:
            return ""
        return "\n".join(f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options))


@dataclass
class PromptLibrary:
    """Collection of prompt templates for various strategies."""

    @staticmethod
    def get_zero_shot() -> PromptTemplate:
        return PromptTemplate(
            system="You are a helpful AI assistant. Answer the following question.",
            user_template="{question}",
        )

    @staticmethod
    def get_chain_of_thought() -> PromptTemplate:
        return PromptTemplate(
            system="You are a helpful AI assistant. Think step by step and show your reasoning.",
            user_template="{question}\n\nLet's think through this step by step:",
        )

    @staticmethod
    def get_few_shot_cot(examples: list[dict[str, str]]) -> PromptTemplate:
        return PromptTemplate(
            system="You are a helpful AI assistant. Think step by step and show your reasoning.",
            user_template="{question}\n\nLet's think through this step by step:",
            examples=examples,
        )

    @staticmethod
    def get_self_critique() -> PromptTemplate:
        return PromptTemplate(
            system="You are a helpful AI assistant. Answer questions and critique your own responses when needed.",
            user_template=(
                "{question}\n\n"
                "First, provide your answer. Then, critically examine your answer and identify any potential issues."
            ),
        )

    @staticmethod
    def get_constitutional() -> PromptTemplate:
        return PromptTemplate(
            system="""You are a helpful AI assistant that follows principles.
Review your response against these principles:
1. Is the answer accurate and factual?
2. Is the answer helpful and relevant?
3. Is the answer safe and ethical?
4. Is the answer concise and clear?

If any principle is violated, revise your response accordingly.""",
            user_template="{question}",
        )

    @staticmethod
    def get_mcq(options: list[str]) -> PromptTemplate:
        return PromptTemplate(
            system="You are a helpful AI assistant. Answer the multiple choice question by selecting the correct letter.",
            user_template=(
                "{question}\n\n"
                "Options:\n"
                "{options}\n\n"
                "Respond with only the letter of the correct answer (e.g., A, B, C, or D)."
            ),
        )

    @staticmethod
    def get_mcq_cot(options: list[str]) -> PromptTemplate:
        return PromptTemplate(
            system="You are a helpful AI assistant. Think step by step, then give your final answer.",
            user_template=(
                "{question}\n\n"
                "Options:\n"
                "{options}\n\n"
                "Let's analyze this step by step:\n"
            ),
        )

    @staticmethod
    def get_math_reasoning() -> PromptTemplate:
        return PromptTemplate(
            system="You are a mathematical reasoning assistant. Show all work step by step.",
            user_template=(
                "{question}\n\n"
                "Please solve this step by step, showing your mathematical reasoning:\n"
            ),
        )

    @staticmethod
    def get_commonsense() -> PromptTemplate:
        return PromptTemplate(
            system="You are a commonsense reasoning assistant. Use practical knowledge and logic.",
            user_template=(
                "{question}\n\n"
                "Consider what would make sense in everyday situations:\n"
            ),
        )

    @classmethod
    def get_for_task(cls, task_type: str, **kwargs: Any) -> PromptTemplate:
        """Get the appropriate prompt template for a task type."""
        strategies = {
            "mcq": cls.get_mcq,
            "mcq_cot": cls.get_mcq_cot,
            "math": cls.get_math_reasoning,
            "commonsense": cls.get_commonsense,
            "cot": cls.get_chain_of_thought,
            "zero_shot": cls.get_zero_shot,
            "self_critique": cls.get_self_critique,
            "constitutional": cls.get_constitutional,
        }

        factory = strategies.get(task_type, cls.get_zero_shot)
        if task_type in ("mcq",):
            return factory(kwargs.get("options", []))
        return factory()


COT_EXAMPLES_MATH = [
    {
        "question": "If John has 5 apples and gives 2 to Mary, how many does he have left?",
        "answer": (
            "Let's think step by step:\n"
            "1. John starts with 5 apples\n"
            "2. He gives 2 apples to Mary\n"
            "3. 5 - 2 = 3\n"
            "John has 3 apples left."
        ),
    },
    {
        "question": "A rectangle has width 4 and length 7. What is its area?",
        "answer": (
            "Let's think step by step:\n"
            "1. The formula for area of a rectangle is length × width\n"
            "2. Area = 7 × 4\n"
            "3. Area = 28\n"
            "The area is 28 square units."
        ),
    },
]

COT_EXAMPLES_COMMON = [
    {
        "question": "You forgot your umbrella and it's starting to rain outside. What should you do?",
        "answer": (
            "Let's think about this practically:\n"
            "1. It's raining and I don't have an umbrella\n"
            "2. Options: wait it out, find shelter, accept getting wet, or improvise\n"
            "3. Best immediate action would be to find cover or wait\n"
            "I should look for shelter or an alternative cover."
        ),
    },
]

COT_EXAMPLES_MCQ = [
    {
        "question": (
            "Which of the following is the largest planet in our solar system?\n"
            "A. Earth\n"
            "B. Mars\n"
            "C. Jupiter\n"
            "D. Venus"
        ),
        "answer": (
            "Let's analyze each option:\n"
            "1. Earth has diameter ~12,742 km\n"
            "2. Mars has diameter ~6,779 km\n"
            "3. Jupiter has diameter ~139,820 km (by far the largest)\n"
            "4. Venus has diameter ~12,104 km\n"
            "Jupiter is the largest planet.\n"
            "Answer: C"
        ),
    },
]


def build_few_shot_prompt(
    question: str,
    strategy: PromptStrategy,
    task_specific_examples: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build a prompt with the given strategy."""
    if strategy == PromptStrategy.ZERO_SHOT:
        return [{"role": "user", "content": question}]

    if strategy == PromptStrategy.CHAIN_OF_THOUGHT:
        template = PromptLibrary.get_chain_of_thought()
        return template.render(question=question)

    if strategy == PromptStrategy.CHAIN_OF_THOUGHT_FEW_SHOT:
        examples = task_specific_examples or COT_EXAMPLES_MATH
        template = PromptLibrary.get_few_shot_cot(examples)
        return template.render(question=question)

    if strategy == PromptStrategy.SELF_CRITIQUE:
        template = PromptLibrary.get_self_critique()
        return template.render(question=question)

    if strategy == PromptStrategy.CONSTITUTIONAL:
        template = PromptLibrary.get_constitutional()
        return template.render(question=question)

    return [{"role": "user", "content": question}]
