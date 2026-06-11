"""Inspect AI tasks for the multi-benchmark data-contamination probe.

Mirrors the structure of the Agentic Misalignment probe in ../../sandbox.ipynb:
a candidate solver (system message + generate) feeding a lenient
``model_graded_qa`` scorer that grades each answer against its per-question
criterion (C / P / I -> 1.0 / 0.5 / 0.0).

The default task ``contamination_probe`` runs all three benchmarks in one eval
(separable later via the ``benchmark`` metadata tag). Per-benchmark wrapper
tasks are also provided for running one benchmark in isolation.

The grader model is configurable; it defaults to the same strong Eliza model
used in the reference probe. The grader's own knowledge of the papers is
irrelevant - it grades only against the supplied criterion.
"""

from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate, system_message

from questions.prompts import CANDIDATE_SYSTEM, GRADER_INSTRUCTIONS

from .dataset import build_samples

# Strong, lenient judge (same family as the reference probe). Override per-call
# via the task argument if you want a different grader.
DEFAULT_GRADER_MODEL = "eliza/anthropic/claude-opus-4-6"

# Repeats per question. Contamination signals are noisy at the single-sample
# level; epochs average them out (the reference used 20).
DEFAULT_EPOCHS = 20


def _make_task(benchmark: str | None, grader_model: str, epochs: int) -> Task:
    return Task(
        dataset=build_samples(benchmark),
        solver=[system_message(CANDIDATE_SYSTEM), generate()],
        scorer=model_graded_qa(
            instructions=GRADER_INSTRUCTIONS,
            partial_credit=True,
            model=grader_model,
        ),
        epochs=epochs,
    )


@task
def contamination_probe(
    grader_model: str = DEFAULT_GRADER_MODEL,
    epochs: int = DEFAULT_EPOCHS,
) -> Task:
    """Combined probe over Cybench + Alignment Faking + IPI Arena.

    Results stay separable by the ``benchmark`` and ``source`` metadata tags.
    """
    return _make_task(None, grader_model, epochs)


@task
def cybench_probe(
    grader_model: str = DEFAULT_GRADER_MODEL,
    epochs: int = DEFAULT_EPOCHS,
) -> Task:
    """Cybench-only contamination probe."""
    return _make_task("cybench", grader_model, epochs)


@task
def alignment_faking_probe(
    grader_model: str = DEFAULT_GRADER_MODEL,
    epochs: int = DEFAULT_EPOCHS,
) -> Task:
    """Alignment Faking-only contamination probe."""
    return _make_task("alignment_faking", grader_model, epochs)


@task
def ipi_arena_probe(
    grader_model: str = DEFAULT_GRADER_MODEL,
    epochs: int = DEFAULT_EPOCHS,
) -> Task:
    """IPI Arena-only contamination probe."""
    return _make_task("ipi_arena", grader_model, epochs)
