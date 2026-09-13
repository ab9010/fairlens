"""
fairness.py
Core fairness/bias calculations for FairLens.

All numbers here are computed live from whatever dataset + column
selections the caller provides. Nothing is hard-coded.
"""
from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd
import numpy as np


class FairnessError(ValueError):
    """Raised when a fairness analysis request can't be completed."""


def _selection_rate(series: pd.Series, positive_value: str) -> float:
    if len(series) == 0:
        return 0.0
    return float((series.astype(str) == str(positive_value)).mean())


def compute_group_stats(
    df: pd.DataFrame,
    protected_attr: str,
    outcome_col: str,
    positive_outcome: str,
) -> List[Dict[str, Any]]:
    groups = []
    for group_value, group_df in df.groupby(protected_attr, dropna=False):
        rate = _selection_rate(group_df[outcome_col], positive_outcome)
        positive_count = int((group_df[outcome_col].astype(str) == str(positive_outcome)).sum())
        groups.append({
            "group": str(group_value),
            "count": int(len(group_df)),
            "positive_count": positive_count,
            "negative_count": int(len(group_df)) - positive_count,
            "selection_rate": round(rate, 4),
        })
    groups.sort(key=lambda g: g["count"], reverse=True)
    return groups


def _true_positive_rate(df: pd.DataFrame, outcome_col: str, positive_outcome: str,
                         label_col: str | None) -> float | None:
    """
    Equal opportunity needs a ground-truth label distinct from the predicted
    outcome (TPR = P(predicted positive | actually positive)). FairLens'
    demo datasets only carry one outcome column, so when no separate ground
    truth label is supplied we cannot compute a true TPR and return None
    rather than fabricate one.
    """
    if not label_col or label_col not in df.columns:
        return None
    positives = df[df[label_col].astype(str) == str(positive_outcome)]
    if len(positives) == 0:
        return None
    return _selection_rate(positives[outcome_col], positive_outcome)


def compute_fairness_score(
    selection_rate_diff: float,
    disparate_impact: float,
) -> float:
    """
    Transparent composite score (0-100), documented in the README.

    - Start at 100.
    - Subtract up to 60 points for selection-rate difference (scaled so a
      50-point gap in selection rates costs the full 60).
    - Subtract up to 40 points for how far disparate impact falls below the
      0.8 "four-fifths rule" reference line (0 impact costs the full 40).

    This is an educational composite, not a legal/regulatory standard.
    """
    rate_penalty = min(60.0, (selection_rate_diff / 0.5) * 60.0)

    if disparate_impact >= 0.8:
        impact_penalty = 0.0
    else:
        impact_penalty = min(40.0, ((0.8 - disparate_impact) / 0.8) * 40.0)

    score = 100.0 - rate_penalty - impact_penalty
    return round(max(0.0, min(100.0, score)), 1)


def score_to_level(score: float) -> Dict[str, str]:
    if score >= 80:
        return {"level": "Relatively Fair", "band": "low"}
    if score >= 60:
        return {"level": "Moderate Disparity", "band": "moderate"}
    if score >= 40:
        return {"level": "High Disparity", "band": "high"}
    return {"level": "Severe Disparity", "band": "severe"}


def analyze_fairness(
    df: pd.DataFrame,
    protected_attr: str,
    outcome_col: str,
    positive_outcome: str,
    ground_truth_col: str | None = None,
) -> Dict[str, Any]:
    if protected_attr not in df.columns:
        raise FairnessError(f"Protected attribute '{protected_attr}' not found in dataset.")
    if outcome_col not in df.columns:
        raise FairnessError(f"Outcome column '{outcome_col}' not found in dataset.")

    working = df[[protected_attr, outcome_col] + ([ground_truth_col] if ground_truth_col else [])].dropna(
        subset=[protected_attr, outcome_col]
    )
    if working.empty:
        raise FairnessError("No usable rows remain after removing missing values.")

    group_stats = compute_group_stats(working, protected_attr, outcome_col, positive_outcome)
    if len(group_stats) < 2:
        raise FairnessError(
            f"Protected attribute '{protected_attr}' must have at least 2 groups; found {len(group_stats)}."
        )

    rates = [g["selection_rate"] for g in group_stats]
    max_group = max(group_stats, key=lambda g: g["selection_rate"])
    min_group = min(group_stats, key=lambda g: g["selection_rate"])

    selection_rate_diff = round(max_group["selection_rate"] - min_group["selection_rate"], 4)
    disparate_impact = round(
        (min_group["selection_rate"] / max_group["selection_rate"]) if max_group["selection_rate"] > 0 else 0.0,
        4,
    )
    demographic_parity = round(1 - selection_rate_diff, 4)  # 1.0 = perfect parity

    tpr = _true_positive_rate(working, outcome_col, positive_outcome, ground_truth_col)

    fairness_score = compute_fairness_score(selection_rate_diff, disparate_impact)
    level_info = score_to_level(fairness_score)

    passes_four_fifths = disparate_impact >= 0.8

    explanation = (
        f"Among {sum(g['count'] for g in group_stats)} records grouped by '{protected_attr}', "
        f"'{max_group['group']}' received a positive '{outcome_col}' outcome "
        f"{max_group['selection_rate']*100:.1f}% of the time, while '{min_group['group']}' received one "
        f"{min_group['selection_rate']*100:.1f}% of the time — a gap of {selection_rate_diff*100:.1f} "
        f"percentage points. The disparate impact ratio is {disparate_impact:.2f} "
        f"({'meets' if passes_four_fifths else 'falls below'} the common 0.80 four-fifths reference line), "
        f"which places this dataset in the '{level_info['level']}' band."
    )

    return {
        "protected_attribute": protected_attr,
        "outcome_column": outcome_col,
        "positive_outcome": str(positive_outcome),
        "row_count": int(len(working)),
        "group_results": group_stats,
        "metrics": {
            "selection_rate_difference": selection_rate_diff,
            "demographic_parity": demographic_parity,
            "disparate_impact": disparate_impact,
            "passes_four_fifths_rule": passes_four_fifths,
            "equal_opportunity_tpr": tpr,
            "max_group": max_group["group"],
            "min_group": min_group["group"],
        },
        "fairness_score": fairness_score,
        "bias_level": level_info["level"],
        "bias_band": level_info["band"],
        "explanation": explanation,
        "recommendations": generate_recommendations(level_info["band"], selection_rate_diff, disparate_impact, group_stats),
    }


def generate_recommendations(
    band: str, selection_rate_diff: float, disparate_impact: float, group_stats: List[Dict[str, Any]]
) -> List[str]:
    recs: List[str] = []

    smallest = min(group_stats, key=lambda g: g["count"])
    total = sum(g["count"] for g in group_stats)
    if smallest["count"] / total < 0.4:
        recs.append(
            f"Review group representation — '{smallest['group']}' makes up only "
            f"{smallest['count']/total*100:.1f}% of the dataset, which can make its outcomes less reliable."
        )

    if band in ("high", "severe"):
        recs.append("Investigate historical patterns in how past outcomes were labeled, since large gaps often trace back to biased historical decisions rather than the applicants themselves.")
        recs.append("Evaluate model or process performance separately for each group instead of relying on one aggregate accuracy number.")
    else:
        recs.append("Evaluate model or process performance separately for each group to confirm the current parity holds beyond this single metric.")

    if disparate_impact < 0.8:
        recs.append("Consider fairness-aware preprocessing (e.g. reweighing or resampling groups) before training or deploying a decision process on this data.")
    else:
        recs.append("Keep monitoring disparate impact over time — parity on one snapshot doesn't guarantee it holds as the underlying data shifts.")

    if selection_rate_diff > 0.05:
        recs.append("Audit the specific features driving decisions to check whether any act as proxies for the protected attribute.")
    else:
        recs.append("Document how each feature relates to the outcome so future proxy effects are easier to catch early.")

    recs.append("Re-test after making changes to confirm the fairness score and disparate impact actually improve, rather than assuming a fix worked.")

    # de-duplicate while preserving order, cap at 6
    seen = set()
    unique = []
    for r in recs:
        if r not in seen:
            unique.append(r)
            seen.add(r)
    return unique[:6]


def simulate_mitigation(group_a_rate: float, group_b_rate: float) -> Dict[str, Any]:
    """
    Educational fairness mitigation simulation: given two arbitrary group
    selection rates (e.g. from the Bias Simulator sliders), compute the
    disparity metrics before mitigation, and what they would look like if
    both groups were nudged halfway toward the average rate (a simple,
    transparent illustration of mitigation — not a scientific correction).
    """
    group_a_rate = max(0.0, min(1.0, group_a_rate))
    group_b_rate = max(0.0, min(1.0, group_b_rate))

    def metrics_for(a: float, b: float) -> Dict[str, float]:
        hi, lo = max(a, b), min(a, b)
        diff = round(hi - lo, 4)
        impact = round((lo / hi) if hi > 0 else 0.0, 4)
        return {
            "group_a_rate": round(a, 4),
            "group_b_rate": round(b, 4),
            "selection_rate_difference": diff,
            "disparate_impact": impact,
            "fairness_score": compute_fairness_score(diff, impact),
        }

    before = metrics_for(group_a_rate, group_b_rate)

    avg = (group_a_rate + group_b_rate) / 2
    mitigated_a = group_a_rate + (avg - group_a_rate) * 0.5
    mitigated_b = group_b_rate + (avg - group_b_rate) * 0.5
    after = metrics_for(mitigated_a, mitigated_b)

    before["bias_level"] = score_to_level(before["fairness_score"])["level"]
    after["bias_level"] = score_to_level(after["fairness_score"])["level"]

    return {"before": before, "after": after}
