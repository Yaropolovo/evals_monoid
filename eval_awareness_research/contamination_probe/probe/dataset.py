"""Assemble Inspect AI ``Sample``s from the three benchmark question banks.

Each question dict (see ../questions/*_questions.py) becomes one ``Sample``:
  - ``input``    : the question STEM only. For MCQ the lettered options are
                   rendered per-epoch by ``probe.solver.shuffle_mcq`` (so the
                   correct answer lands on a random letter each run); for free
                   questions the stem is the whole prompt.
  - ``target``   : the grading criterion (consumed by ``model_graded_qa``). It
                   grades by the *content* of the answer, never by option letter.
  - ``metadata`` : every tag (benchmark, source, group, category, difficulty,
                   format, specificity, n_options) so the analysis can slice
                   along any axis, plus ``options``/``answer`` which the shuffle
                   solver needs at render time.

Question-dict schema
--------------------
Common keys: ``id, benchmark, source, group, category, difficulty, format,
specificity, question, target``.
  - MCQ (``format == "mcq"``) additionally has ``options`` (the *content*
    choices, WITHOUT the abstention option - that is appended by the solver) and
    ``answer`` (the exact text of the correct option, which must be in ``options``;
    for a trap it is the "reject the fabrication" option).
  - Free (``format == "free"``) has neither ``options`` nor ``answer``.

``specificity`` ∈ {``unique``, ``secondary``, ``headline``} records how uniquely
the fact identifies the source: ``unique`` lives only deep in the code/paper;
``headline`` is an abstract/summary fact that leaks into secondary sources and is
therefore a weak contamination signal (kept only as an explicit control).
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
    "incontext_scheming": "questions.incontext_scheming_questions",
}

# Stable display order for benchmarks in the analysis output.
BENCHMARK_ORDER = ["cybench", "alignment_faking", "ipi_arena", "incontext_scheming"]

# Allowed values for the specificity tag (validated).
SPECIFICITY_LEVELS = {"unique", "secondary", "headline"}


def _to_sample(q: dict[str, Any]) -> Sample:
    is_mcq = q["format"] == "mcq"
    # n_options counts the abstention ("I don't know") choice the solver appends.
    n_options = (len(q["options"]) + 1) if is_mcq else None
    return Sample(
        id=q["id"],
        input=q["question"],  # stem only; MCQ options rendered by shuffle_mcq solver
        target=q["target"],
        metadata=dict(
            benchmark=q["benchmark"],
            source=q["source"],            # "code" | "report"
            group=q["group"],              # "knowledge" | "trap"
            category=q.get("category"),
            difficulty=q.get("difficulty"),
            format=q["format"],            # "mcq" | "free"
            specificity=q.get("specificity"),
            n_options=n_options,
            options=list(q["options"]) if is_mcq else None,
            answer=q.get("answer") if is_mcq else None,
        ),
    )


def load_questions(benchmark: str) -> list[dict[str, Any]]:
    """Return the raw question dicts for one benchmark."""
    if benchmark not in BENCHMARK_MODULES:
        raise ValueError(f"unknown benchmark {benchmark!r}; expected one of {list(BENCHMARK_MODULES)}")
    mod = importlib.import_module(BENCHMARK_MODULES[benchmark])
    return list(mod.QUESTIONS)


def validate_questions(benchmark: str | None = None) -> int:
    """Fail-fast structural validation of the question banks.

    Enforces the design invariants (see CLAUDE.md):
      - ids are unique across the validated set;
      - ``group == 'trap'``  ⟺  ``target`` begins with ``[TRAP]``;
      - every MCQ has ``options`` (≥2 content choices) and an ``answer`` that is
        one of those options;
      - ``specificity`` is one of the allowed levels.

    Returns the number of questions validated. Raises ``AssertionError`` on the
    first violation.
    """
    keys = [benchmark] if benchmark is not None else list(BENCHMARK_MODULES)
    questions: list[dict[str, Any]] = []
    for key in keys:
        questions.extend(load_questions(key))

    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), f"duplicate question id(s): {[i for i in ids if ids.count(i) > 1]}"

    for q in questions:
        qid = q["id"]
        is_trap = q["group"] == "trap"
        starts_trap = q["target"].lstrip().startswith("[TRAP]")
        assert is_trap == starts_trap, (
            f"{qid}: group/[TRAP] mismatch - group={q['group']!r} but "
            f"target {'starts' if starts_trap else 'does not start'} with [TRAP]"
        )
        assert q.get("specificity") in SPECIFICITY_LEVELS, (
            f"{qid}: specificity must be one of {sorted(SPECIFICITY_LEVELS)}, got {q.get('specificity')!r}"
        )
        if q["format"] == "mcq":
            opts = q.get("options")
            assert isinstance(opts, list) and len(opts) >= 2, f"{qid}: mcq needs >=2 options"
            assert "answer" in q, f"{qid}: mcq must declare an 'answer'"
            assert q["answer"] in opts, f"{qid}: answer {q['answer']!r} not among options"
            assert q.get("question"), f"{qid}: missing question stem"
        else:
            assert q["format"] == "free", f"{qid}: unknown format {q['format']!r}"
    return len(questions)


def build_samples(benchmark: str | None = None) -> list[Sample]:
    """Build Inspect ``Sample``s (validates the banks first).

    ``benchmark=None`` (default) returns the combined dataset across all three
    banks; passing a key returns just that benchmark's samples.
    """
    validate_questions(benchmark)
    if benchmark is not None:
        return [_to_sample(q) for q in load_questions(benchmark)]
    samples: list[Sample] = []
    for key in BENCHMARK_ORDER:
        samples.extend(_to_sample(q) for q in load_questions(key))
    return samples
