"""Assemble Inspect AI ``Sample``s from the three benchmark question banks.

Each question dict (see ../questions/*_questions.py) becomes one ``Sample``:
  - ``input``  : the formatted question (MCQ options rendered as A./B./... )
  - ``target`` : the grading criterion (consumed by ``model_graded_qa``)
  - ``metadata``: every tag (benchmark, source, group, category, difficulty,
                  format) so the analysis can slice results along any axis.

The combined dataset is the union of all three banks; ``benchmark`` in metadata
keeps them separable in a single eval log.
"""

from __future__ import annotations

import importlib
from typing import Any

from inspect_ai.dataset import Sample

# Map benchmark key -> question-bank module (under the sibling ``questions`` pkg).
BENCHMARK_MODULES: dict[str, str] = {
    "cybench": "questions.cybench_questions",
    "alignment_faking": "questions.alignment_faking_questions",
    "ipi_arena": "questions.ipi_arena_questions",
}

# Stable display order for benchmarks in the analysis output.
BENCHMARK_ORDER = ["cybench", "alignment_faking", "ipi_arena"]

_MCQ_TAIL = "\n\nReply with the letter and the full text of the single best option."


def _format_input(q: dict[str, Any]) -> str:
    """Render a question dict to the candidate-facing prompt string."""
    if q["format"] == "mcq":
        letters = [chr(65 + i) for i in range(len(q["options"]))]
        body = "\n".join(f"{letter}. {opt}" for letter, opt in zip(letters, q["options"]))
        return f"{q['question']}\n\n{body}{_MCQ_TAIL}"
    return q["question"]


def _to_sample(q: dict[str, Any]) -> Sample:
    return Sample(
        id=q["id"],
        input=_format_input(q),
        target=q["target"],
        metadata=dict(
            benchmark=q["benchmark"],
            source=q["source"],          # "code" | "report"
            group=q["group"],            # "knowledge" | "trap"
            category=q.get("category"),
            difficulty=q.get("difficulty"),
            format=q["format"],          # "mcq" | "free"
        ),
    )


def load_questions(benchmark: str) -> list[dict[str, Any]]:
    """Return the raw question dicts for one benchmark."""
    if benchmark not in BENCHMARK_MODULES:
        raise ValueError(f"unknown benchmark {benchmark!r}; expected one of {list(BENCHMARK_MODULES)}")
    mod = importlib.import_module(BENCHMARK_MODULES[benchmark])
    return list(mod.QUESTIONS)


def build_samples(benchmark: str | None = None) -> list[Sample]:
    """Build Inspect ``Sample``s.

    ``benchmark=None`` (default) returns the combined dataset across all three
    banks; passing a key returns just that benchmark's samples.
    """
    if benchmark is not None:
        return [_to_sample(q) for q in load_questions(benchmark)]
    samples: list[Sample] = []
    for key in BENCHMARK_ORDER:
        samples.extend(_to_sample(q) for q in load_questions(key))
    return samples
