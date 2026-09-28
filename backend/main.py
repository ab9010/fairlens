"""
main.py
FairLens FastAPI backend.

Run with:  uvicorn main:app --reload --port 8000
(from inside the backend/ directory)
"""
from __future__ import annotations
import os
import uuid
from typing import Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data_processor import (
    load_csv_from_bytes,
    profile_dataset,
    DataProcessingError,
)
from fairness import analyze_fairness, simulate_mitigation, FairnessError
from report_generator import generate_report_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DEMO_DATASET_PATH = os.path.join(DATA_DIR, "sample_dataset.csv")
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = FastAPI(title="FairLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store keyed by session/dataset id. Simple and transparent —
# fine for an educational single-process demo, not meant for production scale.
_DATASETS: dict[str, pd.DataFrame] = {}
_DATASET_NAMES: dict[str, str] = {}
_LAST_ANALYSIS: dict[str, dict] = {}

DEMO_ID = "demo"


def _get_demo_df() -> pd.DataFrame:
    if DEMO_ID not in _DATASETS:
        if not os.path.exists(DEMO_DATASET_PATH):
            raise HTTPException(status_code=500, detail="Demo dataset file is missing on the server.")
        df = pd.read_csv(DEMO_DATASET_PATH)
        _DATASETS[DEMO_ID] = df
        _DATASET_NAMES[DEMO_ID] = "Synthetic Loan Approval Dataset (demo)"
    return _DATASETS[DEMO_ID]


class AnalyzeRequest(BaseModel):
    dataset_id: str
    protected_attribute: str
    outcome_column: str
    positive_outcome: str
    ground_truth_column: Optional[str] = None


class SimulateRequest(BaseModel):
    group_a_rate: float
    group_b_rate: float


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "FairLens API"}


@app.get("/api/demo-dataset")
def get_demo_dataset():
    df = _get_demo_df()
    profile = profile_dataset(df)
    return {"dataset_id": DEMO_ID, "name": _DATASET_NAMES[DEMO_ID], **profile}


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")
    raw = await file.read()
    try:
        df = load_csv_from_bytes(raw)
    except DataProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dataset_id = str(uuid.uuid4())
    _DATASETS[dataset_id] = df
    _DATASET_NAMES[dataset_id] = file.filename

    profile = profile_dataset(df)
    return {"dataset_id": dataset_id, "name": file.filename, **profile}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    df = _DATASETS.get(req.dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found. Load the demo dataset or upload a CSV first.")

    try:
        result = analyze_fairness(
            df=df,
            protected_attr=req.protected_attribute,
            outcome_col=req.outcome_column,
            positive_outcome=req.positive_outcome,
            ground_truth_col=req.ground_truth_column,
        )
    except FairnessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _LAST_ANALYSIS[req.dataset_id] = {
        "result": result,
        "dataset_name": _DATASET_NAMES.get(req.dataset_id, "dataset"),
    }
    result["dataset_id"] = req.dataset_id
    return result


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    if not (0 <= req.group_a_rate <= 1) or not (0 <= req.group_b_rate <= 1):
        raise HTTPException(status_code=400, detail="Selection rates must be between 0 and 1.")
    return simulate_mitigation(req.group_a_rate, req.group_b_rate)


@app.get("/api/report", response_class=PlainTextResponse)
def report(dataset_id: str = Query(...)):
    entry = _LAST_ANALYSIS.get(dataset_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis found for this dataset. Run /api/analyze first.",
        )
    text = generate_report_text(entry["result"], dataset_name=entry["dataset_name"])
    return PlainTextResponse(
        content=text,
        headers={"Content-Disposition": "attachment; filename=fairlens_report.txt"},
    )


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
