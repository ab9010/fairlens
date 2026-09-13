"""
report_generator.py
Builds a plain-text fairness report from a real analysis result dict
(as produced by fairness.analyze_fairness). No hard-coded values.
"""
from __future__ import annotations
from typing import Any, Dict
from datetime import datetime, timezone


DISCLAIMER = (
    "FairLens is an educational prototype designed to demonstrate concepts in AI "
    "fairness and bias detection. Its metrics and scoring should not be interpreted "
    "as legal, regulatory, medical, financial, or production-model certification."
)


def generate_report_text(analysis: Dict[str, Any], dataset_name: str = "Uploaded dataset") -> str:
    lines = []
    lines.append("=" * 64)
    lines.append("FAIRLENS — AI FAIRNESS REPORT")
    lines.append("=" * 64)
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Dataset: {dataset_name}")
    lines.append(f"Rows analyzed: {analysis['row_count']}")
    lines.append("")
    lines.append("-" * 64)
    lines.append("CONFIGURATION")
    lines.append("-" * 64)
    lines.append(f"Protected attribute: {analysis['protected_attribute']}")
    lines.append(f"Outcome column: {analysis['outcome_column']}")
    lines.append(f"Positive outcome value: {analysis['positive_outcome']}")
    lines.append("")
    lines.append("-" * 64)
    lines.append("FAIRNESS SCORE")
    lines.append("-" * 64)
    lines.append(f"Score: {analysis['fairness_score']} / 100")
    lines.append(f"Bias level: {analysis['bias_level']}")
    lines.append("")
    lines.append("-" * 64)
    lines.append("METRICS")
    lines.append("-" * 64)
    m = analysis["metrics"]
    lines.append(f"Selection rate difference: {m['selection_rate_difference']*100:.2f} percentage points")
    lines.append(f"Demographic parity (1.0 = perfect parity): {m['demographic_parity']}")
    lines.append(f"Disparate impact ratio: {m['disparate_impact']}")
    lines.append(f"Passes four-fifths rule (>= 0.80): {'Yes' if m['passes_four_fifths_rule'] else 'No'}")
    if m.get("equal_opportunity_tpr") is not None:
        lines.append(f"Equal opportunity (true positive rate): {m['equal_opportunity_tpr']}")
    else:
        lines.append("Equal opportunity (true positive rate): not available (no separate ground-truth label provided)")
    lines.append(f"Highest selection rate group: {m['max_group']}")
    lines.append(f"Lowest selection rate group: {m['min_group']}")
    lines.append("")
    lines.append("-" * 64)
    lines.append("GROUP RESULTS")
    lines.append("-" * 64)
    for g in analysis["group_results"]:
        lines.append(
            f"  {g['group']}: n={g['count']}, positive={g['positive_count']}, "
            f"selection rate={g['selection_rate']*100:.2f}%"
        )
    lines.append("")
    lines.append("-" * 64)
    lines.append("INTERPRETATION")
    lines.append("-" * 64)
    lines.append(analysis["explanation"])
    lines.append("")
    lines.append("-" * 64)
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 64)
    for i, rec in enumerate(analysis["recommendations"], start=1):
        lines.append(f"  {i}. {rec}")
    lines.append("")
    lines.append("-" * 64)
    lines.append("DISCLAIMER")
    lines.append("-" * 64)
    lines.append(DISCLAIMER)
    lines.append("=" * 64)

    return "\n".join(lines)
