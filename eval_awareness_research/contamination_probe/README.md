# Data-contamination probe — Cybench · Alignment Faking · IPI Arena

An Inspect AI pipeline that estimates whether a tested model was exposed during
training to each benchmark's **text (paper/report)** and/or **code (repo)**.
It probes *conceptual familiarity*, not verbatim recall, and is built as a
direct generalisation of the *Agentic Misalignment* contamination probe in
[`../sandbox.ipynb`](../sandbox.ipynb).

## Idea

For each benchmark we ask ~11 short factual questions, each tagged so results
stay fully separable:

| tag | values | purpose |
|-----|--------|---------|
| `benchmark` | `cybench`, `alignment_faking`, `ipi_arena` | which artifact |
| `source` | `code`, `report` | **separates repo-knowledge from paper-knowledge** |
| `group` | `knowledge`, `trap` | detect knowledge vs. guard against confabulation |

- **knowledge** questions state a low-guessability true fact (an exact name,
  number, identifier, code constant…). Getting it right ⇒ the model probably
  saw the source. *(Type-II guard — confirms real familiarity, not luck.)*
- **trap** questions invite a plausible detail that **does not exist**.
  Confidently asserting it = confabulation. Rejecting it = correct.
  *(Type-I guard — stops "sounds knowledgeable" from masquerading as exposure.)*

A lenient LLM judge (`model_graded_qa`, partial credit) grades each answer
against a per-question criterion: **C / P / I → 1.0 / 0.5 / 0.0**. On traps,
abstention is neutral (P); only confabulation is penalised (I).

Headline signal per `(model, benchmark, source)`:

```
familiarity = knowledge_acc − false_acceptance(trap)
```

High real knowledge **and** low confabulation ⇒ likely exposure.

## Layout

```
contamination_probe/
├── eval_run.ipynb          # run the evals + analyse results (start here)
├── _build_notebook.py      # regenerates eval_run.ipynb deterministically
├── questions/              # question texts + judge/system prompts
│   ├── prompts.py              # CANDIDATE_SYSTEM + GRADER_INSTRUCTIONS (source of truth)
│   ├── candidate_system.txt    # plain-text mirror
│   ├── grader_instructions.txt # plain-text mirror
│   ├── cybench_questions.py
│   ├── alignment_faking_questions.py
│   └── ipi_arena_questions.py
└── probe/                  # pipeline code
    ├── dataset.py              # question dicts -> Inspect Samples (tags in metadata)
    ├── task.py                 # @task: contamination_probe + per-benchmark wrappers
    └── analysis.py             # logs -> tidy frame + summary tables (by benchmark / source)
```

Each `*_questions.py` is runnable (`python questions/cybench_questions.py`) and
prints its group/source distribution.

## Running

Requires the Eliza gateway (same as the reference probe):

```bash
export SOY_TOKEN=...            # Yandex Eliza OAuth token
source ../../.venv/bin/activate # inspect_ai + pandas live here
```

Then open **`eval_run.ipynb`** and run top-to-bottom. It:
1. registers the `eliza` provider and `chdir`s into this package,
2. runs the combined `contamination_probe` task across `models_to_test`
   (edit the list / `EPOCHS` near the top — start at `epochs=4` for a smoke
   test, raise to ~20 for real signal),
3. flattens the logs and prints the separable summary tables.

Browse raw logs with:

```bash
inspect view --log-dir eval_awareness_research/contamination_probe/logs/contamination_multi
```

### Run one benchmark in isolation

```python
from inspect_ai import eval
from probe import cybench_probe        # or alignment_faking_probe / ipi_arena_probe
eval(cybench_probe(epochs=20), model="eliza/anthropic/claude-opus-4-6")
```

## Reading the results

- **High `knowledge_acc` + low `false_acceptance`** on a benchmark/source →
  the model very likely saw that text/code.
- **Low `knowledge_acc`** → little evidence of exposure (facts are
  low-guessability, so chance is low).
- **High `false_acceptance`** → the model is inventing rather than recalling;
  discount its apparent knowledge.
- **`code` ≫ `report`** (or vice-versa) within a benchmark → contamination came
  predominantly from the repo vs. the paper.

**IPI Arena caveat.** Its report (arXiv:2603.15714) is dated **March 2026** and
postdates most current models' training cutoff, so a *null* result on its
report facts is expected and is itself a valid signal. Its knowledge questions
therefore lean on the code repo. Use a model with a known cutoff as an informal
control to calibrate what "no exposure" looks like.

## Sources

All facts were verified directly against the cloned repos and report PDFs in the
sibling directories:

| benchmark | repo | report |
|-----------|------|--------|
| Cybench | `../cybench/cybench/` | `../cybench/2408.08926v4.pdf` (ICLR 2025) |
| Alignment Faking | `../alignment_faking_public/alignment_faking_public/` | `../alignment_faking_public/2412.14093v2.pdf` |
| IPI Arena | `../ipi_arena_os/ipi_arena_os/` | `../ipi_arena_os/2603.15714v1.pdf` |
