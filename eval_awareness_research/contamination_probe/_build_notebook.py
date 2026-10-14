"""Generate eval_run.ipynb from a list of (cell_type, source) cells.

Kept in the repo so the notebook can be regenerated/edited deterministically
(plain JSON .ipynb is awkward to hand-edit). Run:  python _build_notebook.py
"""
import json
import pathlib

CELLS = [
    ("markdown", """\
# Data-contamination probe — Cybench · Alignment Faking · IPI Arena · In-Context Scheming

Estimate whether a tested model was exposed during training to each benchmark's
**text (paper/report)** and/or **code (repo)** — testing *conceptual familiarity*,
not verbatim recall. Same approach as the *Agentic Misalignment* probe
(`../sandbox.ipynb`), generalised across benchmarks and split by code vs report.

**56 tagged questions** (Cybench 12 · Alignment Faking 14 · IPI Arena 12 · In-Context Scheming 18). Every question carries:
- `benchmark` ∈ {`cybench`, `alignment_faking`, `ipi_arena`, `incontext_scheming`}
- `source` ∈ {`code`, `report`} — lets us separate repo-knowledge from paper-knowledge
- `group` ∈ {`knowledge`, `trap`}
  - **knowledge** — low-guessability true facts. Correct ⇒ the model likely saw the source. *(Type-II guard: detect knowledge.)*
  - **trap** — plausible details that do **not** exist. Confidently asserting one = confabulation. *(Type-I guard: avoid false positives.)* Traps are a **mix of MCQ and free-form**, with the correct MCQ option kept short/symmetric so length never gives it away.
- `specificity` ∈ {`unique`, `secondary`, `headline`} — how uniquely the fact identifies the source. `unique` lives only deep in the code/paper (strong signal); `headline` leaks into abstracts/summaries (weak — kept only as an explicit control).

**Position bias is controlled.** MCQ options are rendered in a **random per-epoch order** (`probe.solver.shuffle_mcq`, seeded by `(question, epoch)`), so the correct answer lands on a different letter each run; the abstention option is always last. Grading is by answer *content*, never by letter.

**Scoring.** A lenient LLM judge (`model_graded_qa`, partial credit) grades *conceptual* correctness (C=1 / P=0.5 / I=0) against a per-question criterion. On traps, abstention is neutral (P); only confabulation is penalised (I).

**Headline signal** per (model, benchmark, source):
`familiarity = knowledge_acc − false_acceptance(trap)` — high real knowledge **and** low confabulation ⇒ likely exposure. Because MCQ has a 1/N guess floor, the analysis also reports `mean_chance` and `knowledge_lift = knowledge_acc − mean_chance` (knowledge *above chance*).

> All facts were verified directly against each cloned repo and report PDF. The question banks live in `questions/`; the task + analysis code in `probe/`.
> **Note on IPI Arena:** its report is dated **March 2026** and postdates most models' training cutoff, so a *null* (no-knowledge) result on its report facts is expected and is itself a valid signal; its knowledge questions lean on the code repo.
> **Note on In-Context Scheming:** its eval code is **non-public** (Apollo withholds it on purpose), so the two sources invert. `report` (the famous Dec-2024 paper) is a **positive control** — ≥2025-cutoff models should score high, proving the probe works. `code` (the private `stand_alone_eval/` Oversight Subversion) is a **negative control** — the *expected* result is ~chance; scoring well above chance on its `unique` facts (esp. the paper-vs-code discriminators, e.g. follow-ups repeated **10** not 20) flags a likely leak. Read the code-vs-report split (§4.2).
> **Re-run required:** any `.eval` logs already in `logs/` predate this question/permutation revision — regenerate them before analysing.
"""),

    ("markdown", "## 1 · Setup\nRegister the Eliza provider and put the probe package on the path. Requires `SOY_TOKEN` in the environment (same as the reference probe). The working directory must be `contamination_probe/` so that `import questions...` and `import probe...` resolve."),

    ("code", """\
import os, sys

# Ensure CWD is the contamination_probe package root (so `questions`/`probe` import).
if os.path.basename(os.getcwd()) != "contamination_probe":
    here = os.path.join(os.getcwd(), "contamination_probe")
    if os.path.isdir(here):
        os.chdir(here)
print("cwd:", os.getcwd())

sys.path.insert(0, os.getcwd())          # for `questions`, `probe`
sys.path.insert(0, os.path.dirname(os.getcwd()))  # for `eliza_provider` (in eval_awareness_research/)

import eliza_provider  # noqa: F401  -- registers the "eliza" model provider

assert os.environ.get("SOY_TOKEN"), "Set SOY_TOKEN before running evals (export SOY_TOKEN=...)."
print("SOY_TOKEN present:", bool(os.environ.get("SOY_TOKEN")))
"""),

    ("code", """\
from probe import (
    contamination_probe,
    cybench_probe, alignment_faking_probe, ipi_arena_probe, incontext_scheming_probe,
    build_samples, validate_questions, DEFAULT_GRADER_MODEL, DEFAULT_EPOCHS,
)
from probe import (
    logs_to_frame, summary_by_benchmark, summary_by_source, summary_by_specificity,
    knowledge_acc_pivot, trap_false_acceptance_pivot, per_question_table,
)

print("grader model:", DEFAULT_GRADER_MODEL, "| default epochs:", DEFAULT_EPOCHS)
"""),

    ("markdown", "## 2 · Models under test\nThe same Eliza model list used in the *Agentic Misalignment* probe. Edit freely — comment lines out for a faster/cheaper run."),

    ("code", """\
models_to_test = [
    "eliza/anthropic/claude-opus-4-1",
    "eliza/anthropic/claude-opus-4-6",
    "eliza/anthropic/claude-opus-4-8",
    "eliza/anthropic/claude-sonnet-4-6",
    "eliza/openai/gpt-4.1",
    "eliza/openai/gpt-5.4",
    "eliza/openai/gpt-5.5",
    "eliza/openai/gpt-5.4-nano-2026-03-17",
]
len(models_to_test)
"""),

    ("markdown", "### Preview the question bank\nValidate the design invariants, sanity-check the composition (incl. `specificity`), and confirm the per-epoch shuffle puts the correct answer on different letters."),

    ("code", """\
from collections import Counter
import random
from probe.solver import render_mcq, _seed

print("validate_questions ->", validate_questions(), "questions OK")  # fails fast on any invariant breach

samples = build_samples()
for axis in ("benchmark", "source", "group", "specificity", "format"):
    print(f" by {axis:11}:", dict(Counter(s.metadata[axis] for s in samples)))

# Show the SAME MCQ rendered for two epochs -> options (and the correct letter) move.
mcq = next(s for s in samples if s.metadata["format"] == "mcq")
print(f"\\n--- {mcq.id} rendered across epochs (answer position is randomised) ---")
for epoch in (1, 2):
    rng = random.Random(_seed(mcq.id, epoch))
    prompt, choices = render_mcq(mcq.input, list(mcq.metadata["options"]), rng)
    letter = chr(65 + choices.index(mcq.metadata["answer"]))
    print(f"\\n[epoch {epoch}] correct answer is now option {letter}:")
    print(prompt)
"""),

    ("markdown", """\
## 3 · Run the probe

One combined eval per model (all four benchmarks, separable later by tag).
`epochs` repeats each question to average out noise — the reference used **20**.
Start small (e.g. `epochs=4`) for a smoke test, then raise it.

Logs are written under `logs/contamination_multi/` and can be browsed with:
`inspect view --log-dir eval_awareness_research/contamination_probe/logs/contamination_multi`
"""),

    ("code", """\
from inspect_ai import eval as inspect_eval

LOG_DIR = "logs/contamination_multi"
EPOCHS = DEFAULT_EPOCHS          # set to e.g. 4 for a quick smoke test
GRADER = DEFAULT_GRADER_MODEL    # the judge grades vs the criterion; its own knowledge is irrelevant

logs = []
for m in models_to_test:
    print(f"=== evaluating: {m} ===")
    try:
        logs.extend(inspect_eval(
            contamination_probe(grader_model=GRADER, epochs=EPOCHS),
            model=m,
            log_dir=LOG_DIR,
            max_tokens=2048,
        ))
    except Exception as e:
        print(f"  FAILED {m}: {type(e).__name__}: {e}")

print(f"\\nCollected {len(logs)} eval log(s). Browse with:  inspect view --log-dir {LOG_DIR}")
"""),

    ("markdown", "### (Optional) reload logs from disk\nIf you restarted the kernel, rebuild `logs` from the saved `.eval` files instead of re-running."),

    ("code", """\
# from inspect_ai.log import list_eval_logs, read_eval_log
# logs = [read_eval_log(p) for p in list_eval_logs(LOG_DIR)]
# print(len(logs), "logs loaded from", LOG_DIR)
"""),

    ("markdown", """\
## 4 · Analysis

`logs_to_frame` flattens everything to one tidy row per (model, question, epoch),
tagged with `benchmark`, `source`, and `group`. Every table below is just a slice
of that frame, so results are fully separable.
"""),

    ("code", """\
df = logs_to_frame(logs)
print("rows:", len(df), "| models:", df.model.nunique())
df.head()
"""),

    ("markdown", "### 4.1 · Headline: familiarity per (model × benchmark)\n`familiarity = knowledge_acc − false_acceptance`. Higher ⇒ stronger evidence the model saw *this benchmark*. `false_acceptance` is the trap confabulation rate (Type-I)."),

    ("code", """\
summary_by_benchmark(df).sort_values(["benchmark", "familiarity"], ascending=[True, False])
"""),

    ("markdown", "### 4.2 · Code vs report — *the* separation\nSplits familiarity by `source`. This answers: did the model's knowledge come from the **repo** or the **paper**? (Traps are tagged by the source their fabrication mimics, so `false_acceptance` is also per-source.)"),

    ("code", """\
summary_by_source(df).sort_values(["benchmark", "source", "familiarity"], ascending=[True, True, False])
"""),

    ("markdown", "### 4.3 · Signal concentration by `specificity` — *a probe sanity check*\nGenuine contamination signal should concentrate on **`unique`** facts (deep code/paper internals), not on **`headline`** facts that leak into abstracts and summaries. If a model only scores on `headline`/`secondary` items, treat its apparent familiarity skeptically — it may know the *gist* without ever seeing the original. `knowledge_lift` here is accuracy above the 1/N guess floor."),

    ("code", """\
summary_by_specificity(df).sort_values(["benchmark", "specificity", "knowledge_lift"], ascending=[True, True, False])
"""),

    ("markdown", "### 4.4 · Compact knowledge-accuracy grid\nKnowledge questions only, as a `model × (benchmark, source)` matrix — the cleanest single view of code-vs-report familiarity."),

    ("code", """\
knowledge_acc_pivot(df)
"""),

    ("markdown", "### 4.5 · Confabulation (trap false-acceptance) per benchmark\nLow is good. A model that fabricates trap details — without genuinely knowing the source — reveals itself here (Type-I errors)."),

    ("code", """\
trap_false_acceptance_pivot(df)
"""),

    ("markdown", "### 4.6 · Per-question detail\n`model × qid` mean scores, grouped by benchmark/source/group/specificity/format. Useful for seeing exactly which facts each model knew (or which traps it fell for)."),

    ("code", """\
per_question_table(df)
"""),

    ("markdown", """\
## 5 · How to read these results

- **High `knowledge_acc` + low `false_acceptance` (⇒ high `familiarity`)** on a benchmark/source: the model very likely saw that text/code in training.
- **Mind the guess floor.** MCQ has a 1/N chance baseline, so read **`knowledge_lift` (= `knowledge_acc − mean_chance`)**, not raw accuracy — a 5-option MCQ scored ~0.2 is just chance. Free-form recall questions have ~0 chance, so they carry the most signal per item.
- **Check `specificity` (§4.3).** The signal should sit on **`unique`** facts. Strong scores confined to **`headline`** facts are uninformative — those leak into secondary write-ups, so a model can know them without the original.
- **Low `knowledge_acc`**: little evidence of exposure. For **IPI Arena's report**, a null is the *expected* result given its 2026 date. (Caveat: a free-form null can also mean the model *declined* to reproduce a string, not that it lacked the knowledge — the banks avoid refusal-prone recall, but keep this in mind.)
- **In-Context Scheming reads inverted.** Its `code` is private, so the *expected* result is `report` **high** (positive control — the Dec-2024 paper is famous) and `code` **at chance** (negative control). The finding to look for is therefore `code` *above* chance on `unique` facts — and especially the discriminators where the paper and code disagree (follow-ups repeated **10** not 20; the `be_honest` variant appends **"Be honest!"** not "Be 100% honest."). A model answering those the *code* way knew the private source, not just the paper.
- **High `false_acceptance` (confabulation)**: the model is guessing/inventing rather than recalling — discount any apparent knowledge as unreliable, and treat familiarity skeptically.
- **Code ≫ report (or vice-versa)** within a benchmark: contamination came predominantly from the **repo** vs the **paper** — a concrete, separable finding.

Use a same-family model with a *known* training cutoff as an informal control: a benchmark released after that cutoff should show near-zero familiarity, calibrating what "no exposure" looks like for these questions.
"""),
]


def main() -> None:
    nb = {
        "cells": [
            {
                "cell_type": ctype,
                "metadata": {},
                "source": src.splitlines(keepends=True),
                **({"outputs": [], "execution_count": None} if ctype == "code" else {}),
            }
            for ctype, src in CELLS
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out = pathlib.Path(__file__).with_name("eval_run.ipynb")
    out.write_text(json.dumps(nb, indent=1) + "\n")
    print(f"wrote {out} ({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
