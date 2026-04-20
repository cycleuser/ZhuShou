"""Advanced prompting strategies: Tree of Thoughts, ReAct, Reflexion, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .prompts import PromptTemplate


@dataclass
class TreeNode:
    """A node in the Tree of Thoughts."""

    thought: str
    children: list["TreeNode"] = field(default_factory=list)
    value: float = 0.0
    is_terminal: bool = False


class TreeOfThoughts:
    """Tree of Thoughts prompting strategy.
    
    Reference: Yao et al., "Tree of Thoughts: Deliberate Problem Solving
    with Large Language Models", NeurIPS 2023.
    """

    def __init__(self, llm_client: Any, max_depth: int = 3, branching_factor: int = 3):
        self._client = llm_client
        self._max_depth = max_depth
        self._branching_factor = branching_factor

    def solve(self, problem: str, temperature: float = 0.7) -> str:
        """Solve a problem using Tree of Thoughts."""
        root = TreeNode(thought="")
        self._expand(root, problem, depth=0, temperature=temperature)
        best_leaf = self._find_best_leaf(root)
        return best_leaf.thought

    def _expand(self, node: TreeNode, problem: str, depth: int, temperature: float):
        """Recursively expand the tree."""
        if depth >= self._max_depth:
            node.is_terminal = True
            return

        prompt = self._generate_thoughts_prompt(problem, node.thought, depth)
        try:
            response = self._client.chat(messages=[{"role": "user", "content": prompt}], temperature=temperature)
            thoughts = self._parse_thoughts(response.content)

            for thought in thoughts[: self._branching_factor]:
                child = TreeNode(thought=thought)
                node.children.append(child)
                child.value = self._evaluate_thought(thought, problem, temperature)
                self._expand(child, problem, depth + 1, temperature)
        except Exception:
            node.is_terminal = True

    def _generate_thoughts_prompt(self, problem: str, current_thought: str, depth: int) -> str:
        """Generate prompt for thought expansion."""
        if depth == 0:
            return f"""Given the problem: "{problem}"

Generate {self._branching_factor} different approaches to solve this problem.
Each approach should be a distinct strategy.

Approaches:"""
        else:
            return f"""Current approach: "{current_thought}"
Problem: "{problem}"

Generate {self._branching_factor} next steps to continue this approach.
Each step should be a concrete action or reasoning step.

Next steps:"""

    def _parse_thoughts(self, content: str) -> list[str]:
        """Parse generated thoughts."""
        thoughts = []
        for line in content.split("\n"):
            line = line.strip()
            if line and len(line) > 10:
                thoughts.append(line)
        return thoughts

    def _evaluate_thought(self, thought: str, problem: str, temperature: float) -> float:
        """Evaluate the quality of a thought."""
        prompt = f"""Evaluate how promising this approach is for solving the problem.
Problem: {problem}
Approach: {thought}

Rate from 0.0 (very poor) to 1.0 (excellent). Respond with only a number."""
        try:
            response = self._client.chat(messages=[{"role": "user", "content": prompt}], temperature=temperature)
            content = response.content.strip()
            for token in content.split():
                try:
                    return float(token)
                except ValueError:
                    continue
        except Exception:
            pass
        return 0.5

    def _find_best_leaf(self, node: TreeNode) -> TreeNode:
        """Find the best leaf node."""
        if not node.children:
            return node
        return max((self._find_best_leaf(child) for child in node.children), key=lambda n: n.value)


class ReActPrompting:
    """ReAct (Reasoning + Acting) prompting strategy.
    
    Reference: Yao et al., "ReAct: Synergizing Reasoning and Acting in
    Language Models", ICLR 2023.
    """

    def __init__(self, llm_client: Any, max_steps: int = 5):
        self._client = llm_client
        self._max_steps = max_steps

    def solve(self, problem: str, temperature: float = 0.3) -> str:
        """Solve using ReAct loop."""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that uses ReAct (Reasoning + Acting) to solve problems. "
                "For each step, first think about what to do (Thought), then take an action (Action), "
                "then observe the result (Observation). Continue until you have the final answer.",
            },
            {"role": "user", "content": f"Problem: {problem}\n\nLet's solve this step by step using Thought, Action, Observation format."},
        ]

        for step in range(self._max_steps):
            messages.append(
                {
                    "role": "assistant",
                    "content": f"Thought {step + 1}: Let me think about what to do next.\n"
                    f"Action {step + 1}: I will analyze the problem and reason through it.\n"
                    f"Observation {step + 1}: I've made progress on understanding the problem.",
                }
            )

        messages.append({"role": "user", "content": "Based on your reasoning, what is the final answer?"})

        try:
            response = self._client.chat(messages=messages, temperature=temperature)
            return response.content
        except Exception as e:
            return f"Error in ReAct: {e}"


class Reflexion:
    """Reflexion: Self-reflection and learning from mistakes.
    
    Reference: Shinn et al., "Reflexion: Language Agents with Verbal
    Reinforcement Learning", NeurIPS 2023.
    """

    def __init__(self, llm_client: Any, max_trials: int = 3):
        self._client = llm_client
        self._max_trials = max_trials
        self._memory: list[str] = []

    def solve(self, problem: str, answer_checker: Any | None = None, temperature: float = 0.3) -> str:
        """Solve with reflexion loop."""
        best_answer = ""
        best_score = 0

        for trial in range(self._max_trials):
            response = self._attempt(problem, trial, temperature)
            answer = self._extract_answer(response)

            if answer_checker:
                score = answer_checker(answer)
            else:
                score = self._self_evaluate(problem, answer, temperature)

            if score > best_score:
                best_score = score
                best_answer = answer

            if score >= 0.9:
                break

            self._memory.append(f"Trial {trial + 1}: {answer} (score: {score:.2f})")

        return best_answer

    def _attempt(self, problem: str, trial: int, temperature: float) -> str:
        """Make an attempt to solve the problem."""
        prompt = f"Problem: {problem}\n"
        if self._memory:
            prompt += "\nPrevious attempts and feedback:\n" + "\n".join(self._memory)
            prompt += "\nBased on previous feedback, try a different approach."
        prompt += "\n\nYour answer:"

        try:
            response = self._client.chat(messages=[{"role": "user", "content": prompt}], temperature=temperature)
            return response.content
        except Exception:
            return ""

    def _self_evaluate(self, problem: str, answer: str, temperature: float) -> float:
        """Self-evaluate the answer quality."""
        prompt = f"""Evaluate this answer to the problem.
Problem: {problem}
Answer: {answer}

Rate the answer quality from 0.0 (completely wrong) to 1.0 (perfect).
Consider: correctness, completeness, clarity.
Respond with only a number."""

        try:
            response = self._client.chat(messages=[{"role": "user", "content": prompt}], temperature=temperature)
            content = response.content.strip()
            for token in content.split():
                try:
                    return max(0.0, min(1.0, float(token)))
                except ValueError:
                    continue
        except Exception:
            pass
        return 0.5

    def _extract_answer(self, content: str) -> str:
        """Extract the answer from content."""
        return content.strip()


class StepBackPrompting:
    """Step-Back Prompting: Abstract and generalize before solving.
    
    Reference: Zheng et al., "Take a Step Back: Evoking Reasoning via
    Abstraction in Large Language Models", ICLR 2024.
    """

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def solve(self, problem: str, temperature: float = 0.3) -> str:
        """Solve using step-back prompting."""
        step_back_prompt = f"""Given the specific question: "{problem}"

First, identify the underlying principle or concept.
What is the more general, abstract version of this question?

Step-Back Question:"""

        try:
            step_back_response = self._client.chat(
                messages=[{"role": "user", "content": step_back_prompt}],
                temperature=temperature,
            )
            step_back_question = step_back_response.content

            step_back_answer_prompt = f"""Answer this general question:
{step_back_question}

Provide a clear, principled answer."""

            step_back_answer_response = self._client.chat(
                messages=[{"role": "user", "content": step_back_answer_prompt}],
                temperature=temperature,
            )

            final_prompt = f"""Now use this general knowledge to answer the specific question:
Original Question: {problem}
General Principle: {step_back_answer_response.content}

Specific Answer:"""

            final_response = self._client.chat(
                messages=[{"role": "user", "content": final_prompt}],
                temperature=temperature,
            )
            return final_response.content
        except Exception as e:
            return f"Error in Step-Back: {e}"


class LeastToMost:
    """Least-to-Most Prompting: Decompose complex problems.
    
    Reference: Zhou et al., "Least-to-Most Prompting Enables Complex
    Reasoning in Large Language Models", ICLR 2023.
    """

    def __init__(self, llm_client: Any):
        self._client = llm_client

    def solve(self, problem: str, temperature: float = 0.3) -> str:
        """Solve using least-to-most prompting."""
        decompose_prompt = f"""Break down this complex problem into simpler sub-problems:
"{problem}"

List the sub-problems from easiest to hardest.
Sub-problems:"""

        try:
            decompose_response = self._client.chat(
                messages=[{"role": "user", "content": decompose_prompt}],
                temperature=temperature,
            )
            sub_problems = self._parse_sub_problems(decompose_response.content)

            answers = []
            for sub_problem in sub_problems:
                context = "\n".join(answers) if answers else ""
                solve_prompt = f"""Context: {context}

Solve this sub-problem: {sub_problem}

Answer:"""

                sub_response = self._client.chat(
                    messages=[{"role": "user", "content": solve_prompt}],
                    temperature=temperature,
                )
                answers.append(f"Q: {sub_problem}\nA: {sub_response.content}")

            final_prompt = f"""Based on the solutions to the sub-problems:
{'\n\n'.join(answers)}

Now solve the original problem: {problem}

Final Answer:"""

            final_response = self._client.chat(
                messages=[{"role": "user", "content": final_prompt}],
                temperature=temperature,
            )
            return final_response.content
        except Exception as e:
            return f"Error in Least-to-Most: {e}"

    def _parse_sub_problems(self, content: str) -> list[str]:
        """Parse sub-problems from content."""
        problems = []
        for line in content.split("\n"):
            line = line.strip()
            if line and len(line) > 10:
                problems.append(line)
        return problems


class GraphOfThoughts:
    """Graph of Thoughts: Non-linear thought organization.
    
    Reference: Besta et al., "Graph of Thoughts: Solving Elaborate
    Problems with Large Language Models", AAAI 2024.
    """

    def __init__(self, llm_client: Any, max_iterations: int = 3):
        self._client = llm_client
        self._max_iterations = max_iterations

    def solve(self, problem: str, temperature: float = 0.7) -> str:
        """Solve using graph of thoughts."""
        thoughts: list[str] = []

        for iteration in range(self._max_iterations):
            if iteration == 0:
                prompt = f"""Generate 3 different perspectives on this problem:
"{problem}"

Perspectives:"""
            else:
                prompt = f"""Given previous thoughts:
{'\n'.join(thoughts)}

Generate new insights by combining or contrasting these thoughts.
New insights:"""

            try:
                response = self._client.chat(messages=[{"role": "user", "content": prompt}], temperature=temperature)
                new_thoughts = self._parse_thoughts(response.content)
                thoughts.extend(new_thoughts[:3])
            except Exception:
                break

        synthesize_prompt = f"""Synthesize these thoughts into a coherent answer:
{'\n'.join(thoughts)}

Problem: {problem}

Synthesized Answer:"""

        try:
            response = self._client.chat(
                messages=[{"role": "user", "content": synthesize_prompt}],
                temperature=temperature,
            )
            return response.content
        except Exception as e:
            return f"Error in Graph of Thoughts: {e}"

    def _parse_thoughts(self, content: str) -> list[str]:
        """Parse thoughts from content."""
        thoughts = []
        for line in content.split("\n"):
            line = line.strip()
            if line and len(line) > 10:
                thoughts.append(line)
        return thoughts
