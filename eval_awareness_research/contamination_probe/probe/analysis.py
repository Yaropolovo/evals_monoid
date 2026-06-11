"""Analysis helpers for the multi-benchmark contamination probe.

Turns a list of Inspect ``EvalLog``s into tidy pandas frames and summary tables.
The central requirement is **separability**: every metric can be sliced by
``model``, ``benchmark``, and ``source`` (code vs report), so we can tell apart

  - which *benchmark* a model is familiar with, and
  - whether that familiarity comes from the *code repo* or the *paper/report*.

Scoring follows the reference probe:
  C / P / I  ->  1.0 / 0.5 / 0.0

Per-(model, benchmark[, source]) we report, over the KNOWLEDGE items vs the
TRAP items separately:
  knowledge_acc    : mean score on knowledge questions (Type-II: detect knowledge)
  trap_rejection   : fraction of traps correctly rejected (score == 1.0)
  false_acceptance : fraction of traps confabulated (score == 0.0)  [Type-I]
  familiarity      : knowledge_acc - false_acceptance
                     (high real knowledge AND low confabulation => exposure)

A model that truly saw a source should score HIGH knowledge_acc with LOW
false_acceptance. A model merely guessing tends to score low knowledge_acc
and/or high false_acceptance, pulling familiarity toward (or below) zero.
"""

from __future__ import annotations

import pandas as pd

# Score-string -> float (model_graded_qa with partial_credit emits C/P/I).
_SCORE_MAP = {
    "C": 1.0, "P": 0.5, "I": 0.0,
    "CORRECT": 1.0, "PARTIAL": 0.5, "INCORRECT": 0.0,
}


def _score_to_float(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    return _SCORE_MAP.get(str(v).upper(), float("nan"))


def logs_to_frame(logs) -> pd.DataFrame:
    """Flatten Inspect ``EvalLog``s into one tidy row per (model, sample, epoch).

    Columns: model, qid, benchmark, source, group, category, difficulty, fmt, score.
    """
    rows: list[dict] = []
    for log in logs:
        model = log.eval.model
        if not log.samples:
            print(f"(no samples for {model} - status={getattr(log, 'status', '?')})")
            continue
        for s in log.samples:
            val = list(s.scores.values())[0].value if s.scores else None
            md = s.metadata or {}
            rows.append(dict(
                model=model,
                qid=s.id,
                benchmark=md.get("benchmark"),
                source=md.get("source"),
                group=md.get("group"),
                category=md.get("category"),
                difficulty=md.get("difficulty"),
                fmt=md.get("format"),
                score=_score_to_float(val),
            ))
    return pd.DataFrame(rows)


def _familiarity_metrics(g: pd.DataFrame) -> pd.Series:
    """Knowledge / trap metrics for one group of rows (already filtered)."""
    know = g.loc[g.group == "knowledge", "score"]
    trap = g.loc[g.group == "trap", "score"]
    false_acc = (trap == 0.0).mean() if len(trap) else float("nan")
    know_acc = know.mean() if len(know) else float("nan")
    return pd.Series(dict(
        knowledge_acc=know_acc,
        trap_rejection=(trap == 1.0).mean() if len(trap) else float("nan"),
        false_acceptance=false_acc,
        familiarity=know_acc - false_acc,
        n_items=int(g["qid"].nunique()),
        n_samples=len(g),
    ))


def summary_by_benchmark(df: pd.DataFrame) -> pd.DataFrame:
    """Per (model, benchmark) familiarity summary - the headline table."""
    out = (df.groupby(["model", "benchmark"], dropna=False)
             .apply(_familiarity_metrics, include_groups=False)
             .round(3))
    return out


def summary_by_source(df: pd.DataFrame) -> pd.DataFrame:
    """Per (model, benchmark, source) summary - separates CODE vs REPORT knowledge.

    This is the table that answers "did familiarity come from the repo or the
    paper?". Note: traps are tagged by the source their fabrication mimics, so
    false_acceptance is reported per source. A (benchmark, source) slice with no
    trap items shows NaN for trap_rejection / false_acceptance / familiarity -
    read knowledge_acc there (or use knowledge_acc_pivot, and summary_by_benchmark
    for a familiarity figure that always has traps in its denominator).
    """
    out = (df.groupby(["model", "benchmark", "source"], dropna=False)
             .apply(_familiarity_metrics, include_groups=False)
             .round(3))
    return out


def knowledge_acc_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Compact model x (benchmark, source) table of KNOWLEDGE accuracy only.

    The cleanest single view of code-vs-report familiarity per benchmark.
    """
    know = df[df.group == "knowledge"]
    return (know.pivot_table(index="model", columns=["benchmark", "source"],
                             values="score", aggfunc="mean")
                .round(2))


def trap_false_acceptance_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """model x benchmark table of trap false-acceptance (confabulation rate)."""
    trap = df[df.group == "trap"]
    return (trap.assign(confab=(trap.score == 0.0).astype(float))
                .pivot_table(index="model", columns="benchmark",
                             values="confab", aggfunc="mean")
                .round(2))


def per_question_table(df: pd.DataFrame) -> pd.DataFrame:
    """model x qid mean score - useful for eyeballing which exact facts landed."""
    return (df.pivot_table(index=["benchmark", "source", "group", "qid"],
                           columns="model", values="score", aggfunc="mean")
              .round(2))
