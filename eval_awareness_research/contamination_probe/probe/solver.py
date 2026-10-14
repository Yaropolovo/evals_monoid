"""Per-epoch multiple-choice option shuffling for the contamination probe.

Why this exists
---------------
The candidate prompt for an MCQ is rendered *here*, at solve time, instead of
being baked into ``Sample.input`` once. That lets us re-shuffle the option order
on **every epoch** so the correct answer lands on a different letter each run,
removing position (primacy/recency) bias from the aggregate score.

Design
------
- The Sample carries only the question *stem* in ``input``; the content options
  and the correct ``answer`` live in ``metadata`` (see ``probe/dataset.py``).
- For each (sample, epoch) we derive a deterministic, reproducible RNG seed from
  ``crc32("<id>:<epoch>")`` - note that Python's builtin ``hash()`` is salted per
  process and would NOT be reproducible across runs.
- Only the *content* options are shuffled. The abstention option ("I don't know")
  is always appended last: it is never the correct answer, so its fixed position
  cannot bias the position of the *correct* answer, and keeping it last reads
  naturally. Trap "None of these ..." options are ordinary content options and
  therefore DO get shuffled.
- Grading is done by ``model_graded_qa`` against the criterion *text*, so the
  shuffled letters never need to be reconciled with the target - the candidate
  echoes the full option text, which is stable across shuffles.

The realised order and the correct answer's letter are stashed back into
``state.metadata`` (``mcq_order`` / ``answer_letter``) so a later audit can check
that correct-answer positions are actually balanced across epochs.
"""

from __future__ import annotations

import random
import zlib

from inspect_ai.solver import Generate, Solver, TaskState, solver

# Abstention option, appended last on every MCQ (mirrors questions/*_questions.py).
IDK = "Not specified / I don't know"

# Instruction tail shown after the lettered options.
MCQ_TAIL = "\n\nReply with the letter and the full text of the single best option."


def _seed(sample_id: object, epoch: int) -> int:
    """Deterministic, cross-run-stable seed for one (sample, epoch)."""
    return zlib.crc32(f"{sample_id}:{epoch}".encode())


def render_mcq(stem: str, options: list[str], rng: random.Random) -> tuple[str, list[str]]:
    """Return (prompt_text, shuffled_choices_incl_IDK).

    ``options`` are the content choices (without IDK). They are shuffled with
    ``rng``; IDK is appended last. The returned choice list is in displayed order.
    """
    shuffled = list(options)
    rng.shuffle(shuffled)
    choices = shuffled + [IDK]
    letters = [chr(65 + i) for i in range(len(choices))]
    body = "\n".join(f"{letter}. {opt}" for letter, opt in zip(letters, choices))
    return f"{stem}\n\n{body}{MCQ_TAIL}", choices


@solver
def shuffle_mcq() -> Solver:
    """Render MCQ options in a per-epoch random order into the user prompt.

    No-op for free-form questions (``metadata['format'] != 'mcq'``). Place this
    between ``system_message(...)`` and ``generate()`` in the solver chain.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        md = state.metadata or {}
        if md.get("format") != "mcq":
            return state

        options = list(md.get("options") or [])
        if not options:
            return state  # nothing to render; leave the stem as-is

        stem = state.user_prompt.text
        rng = random.Random(_seed(state.sample_id, state.epoch))
        prompt, choices = render_mcq(stem, options, rng)
        state.user_prompt.text = prompt

        # Audit trail: realised order + which letter the correct answer landed on.
        answer = md.get("answer")
        state.metadata["mcq_order"] = choices
        if answer in choices:
            state.metadata["answer_letter"] = chr(65 + choices.index(answer))
        return state

    return solve
