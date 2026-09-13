"""
data_processor.py
Loading, validating and profiling datasets (demo or user-uploaded) for FairLens.
"""
from __future__ import annotations
from typing import Any, Dict, List
import io
import pandas as pd
import numpy as np


class DataProcessingError(ValueError):
    """Raised when a CSV can't be parsed or is unusable."""


MAX_PREVIEW_ROWS = 15
MAX_ROWS_ACCEPTED = 200_000


def load_csv_from_bytes(raw: bytes) -> pd.DataFrame:
    if not raw:
        raise DataProcessingError("The uploaded file is empty.")
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
        except Exception as exc:
            raise DataProcessingError(f"Could not decode CSV file: {exc}") from exc
    except pd.errors.EmptyDataError as exc:
        raise DataProcessingError("The CSV file has no columns to parse.") from exc
    except pd.errors.ParserError as exc:
        raise DataProcessingError(f"The CSV file is malformed: {exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"Could not read CSV file: {exc}") from exc

    return validate_dataframe(df)


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise DataProcessingError("The dataset has no rows.")
    if len(df.columns) < 2:
        raise DataProcessingError("The dataset needs at least two columns to analyze fairness.")
    if len(df) > MAX_ROWS_ACCEPTED:
        raise DataProcessingError(f"Dataset too large ({len(df)} rows). Limit is {MAX_ROWS_ACCEPTED}.")

    # De-duplicate column names to avoid downstream ambiguity
    df.columns = [str(c).strip() for c in df.columns]
    if len(set(df.columns)) != len(df.columns):
        raise DataProcessingError("The CSV has duplicate column names.")

    return df


def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]

    missing_values = {col: int(df[col].isna().sum()) for col in df.columns}
    total_missing = int(sum(missing_values.values()))

    # candidate protected attributes / outcomes: categorical columns with a
    # small number of distinct values are the most plausible choices
    likely_categorical_candidates = [
        c for c in categorical_cols
        if 2 <= df[c].nunique(dropna=True) <= 10
    ]

    preview_df = df.head(MAX_PREVIEW_ROWS).copy()
    preview_df = preview_df.where(pd.notnull(preview_df), None)

    # unique values for small-cardinality columns, used by the frontend to
    # populate protected-attribute / outcome / positive-outcome dropdowns
    column_unique_values = {
        c: sorted(df[c].dropna().astype(str).unique().tolist())
        for c in likely_categorical_candidates
    }

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "candidate_attribute_columns": likely_categorical_candidates,
        "column_unique_values": column_unique_values,
        "missing_values": missing_values,
        "total_missing": total_missing,
        "preview_rows": preview_df.to_dict(orient="records"),
    }


def get_column_unique_values(df: pd.DataFrame, column: str, limit: int = 20) -> List[str]:
    if column not in df.columns:
        raise DataProcessingError(f"Column '{column}' not found in dataset.")
    values = df[column].dropna().astype(str).unique().tolist()
    return sorted(values)[:limit]
