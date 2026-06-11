"""Helper package for the multi-benchmark data-contamination probe.

Public surface:
  - tasks:    contamination_probe, cybench_probe, alignment_faking_probe,
              ipi_arena_probe  (Inspect AI @task functions)
  - dataset:  build_samples, load_questions, BENCHMARK_ORDER
  - analysis: logs_to_frame, summary_by_benchmark, summary_by_source,
              knowledge_acc_pivot, trap_false_acceptance_pivot, per_question_table
"""

from .analysis import (
    knowledge_acc_pivot,
    logs_to_frame,
    per_question_table,
    summary_by_benchmark,
    summary_by_source,
    trap_false_acceptance_pivot,
)
from .dataset import BENCHMARK_ORDER, build_samples, load_questions
from .task import (
    DEFAULT_EPOCHS,
    DEFAULT_GRADER_MODEL,
    alignment_faking_probe,
    contamination_probe,
    cybench_probe,
    ipi_arena_probe,
)

__all__ = [
    "contamination_probe",
    "cybench_probe",
    "alignment_faking_probe",
    "ipi_arena_probe",
    "DEFAULT_GRADER_MODEL",
    "DEFAULT_EPOCHS",
    "build_samples",
    "load_questions",
    "BENCHMARK_ORDER",
    "logs_to_frame",
    "summary_by_benchmark",
    "summary_by_source",
    "knowledge_acc_pivot",
    "trap_false_acceptance_pivot",
    "per_question_table",
]
