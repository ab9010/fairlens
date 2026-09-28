# FairLens

**Detect Bias. Measure Fairness. Build Responsible AI.**

FairLens is an educational web platform for exploring AI fairness and bias
detection. Upload a CSV (or use the built-in synthetic loan-approval
dataset), pick a protected attribute and an outcome column, and FairLens
runs real, transparent fairness calculations — no hard-coded results — and
returns a dashboard with a fairness score, group-level metrics, charts, a
plain-language explanation, recommendations, and a downloadable report.

This project was built as a college social internship project on **AI
Ethics — Bias Detection**.

## Features

- **Fairness Lab** — load the demo dataset or upload a CSV, preview it,
  choose a protected attribute / outcome / positive outcome, and run a live
  fairness test against the FastAPI backend.
- **Results Dashboard** — fairness score, bias severity band, per-metric
  cards, group selection-rate table, five Chart.js visualizations, a
  generated "why was bias detected" explanation, and 4–6 dynamically
  generated recommendations.
- **Educational mitigation simulation** — an illustrative before/after view
  showing what nudging group selection rates toward parity would do to the
  metrics (explicitly labeled as a simulation, not a retrained model).
- **Bias Simulator** — two sliders let you set two arbitrary group
  selection rates and watch the selection-rate gap, disparate impact, and
  fairness score update live.
- **Learn page** — plain-language explanations of AI ethics, bias types
  (dataset, historical, representation, measurement, algorithmic), and the
  six Responsible AI principles (fairness, transparency, accountability,
  privacy, safety, explainability), plus the fairness score formula.
- **Downloadable fairness report** — a plain-text report built from the
  same analysis object shown on the dashboard, including a disclaimer.

## Technology stack

- **Frontend:** HTML5, CSS3, vanilla JavaScript, Chart.js (via CDN)
- **Backend:** Python, FastAPI, Uvicorn
- **Data / ML:** Pandas, NumPy

## Folder structure

```text
FairLens/
├── frontend/
│   ├── index.html          Homepage
│   ├── bias-test.html      Fairness Lab (dataset → columns → run test)
│   ├── simulator.html      Bias Simulator (two-slider live demo)
│   ├── results.html        Results dashboard (reads last analysis)
│   ├── learn.html          AI ethics & bias concepts
│   ├── about.html          Project background
│   ├── css/                style.css (shared tokens) + one file per page
│   └── js/                 api.js (fetch wrapper), main.js (nav), page scripts
├── backend/
│   ├── main.py              FastAPI app & routes
│   ├── fairness.py          Fairness metric calculations & scoring
│   ├── data_processor.py    CSV loading, validation, profiling
│   └── report_generator.py  Plain-text report builder
├── data/
│   └── sample_dataset.csv   Synthetic demo dataset (420 rows)
├── reports/                  (reports are generated on demand, not stored)
├── requirements.txt
└── README.md
```

## Fairness calculations

All metrics are computed live in `backend/fairness.py` from whichever
dataset and columns the request specifies — nothing is hard-coded.

- **Group selection rate** — share of each group's rows with the chosen
  positive outcome value.
- **Selection rate difference** — gap, in percentage points, between the
  highest- and lowest-rate groups.
- **Demographic parity** — `1 − selection rate difference` (1.0 = perfect
  parity).
- **Disparate impact** — ratio of the lowest group's rate to the highest
  group's rate. The common "four-fifths rule" flags ratios below 0.80.
- **Equal opportunity (TPR)** — true positive rate per group, computed only
  when a separate ground-truth label column is supplied (the demo dataset
  only has one outcome column, so this is `null` for it — FairLens never
  fabricates a value it can't actually compute).
- **Fairness score (0–100)** — starts at 100, subtracts up to 60 points for
  the selection rate difference (scaled against a 50-point gap) and up to
  40 points for how far disparate impact falls below 0.80. See
  `compute_fairness_score()` for the exact formula.

  | Score | Band |
  |---|---|
  | 80–100 | Relatively Fair |
  | 60–79 | Moderate Disparity |
  | 40–59 | High Disparity |
  | 0–39 | Severe Disparity |

This is an **educational composite score**, not an official scientific,
legal, or regulatory fairness standard.

## Synthetic dataset

`data/sample_dataset.csv` is a synthetic loan-approval dataset (420 rows)
generated with NumPy/Pandas (`age, gender, income, education,
employment_years, credit_score, loan_amount, approved`). Approval is driven
mainly by credit score, income, and employment history, with a deliberate,
moderate gender disparity injected on top (~20-point gap in approval rates)
so the demo has something real to detect. It is a **synthetic demonstration
dataset created for educational purposes** — it does not describe real
people or a real lender.

## Installation

```bash
git clone <this-repo>
cd FairLens
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`. Interactive docs are
at `http://localhost:8000/docs`.

## Running the frontend

The frontend is static HTML/CSS/JS, so any static file server works:

```bash
cd frontend
python3 -m http.server 5500
```

Then open `http://localhost:5500/index.html`. The frontend calls the
backend at `http://localhost:8000/api` (see `frontend/js/api.js`) — update
`BASE` there if you host the backend elsewhere. CORS is open (`*`) on the
backend for local development.

## Deploying on Render

FairLens is configured as a single Render web service. FastAPI serves the
frontend and API from the same host, so the browser uses the deployed origin
for API requests automatically.

1. Push this project to a Git repository.
2. In Render, choose **New > Blueprint** and connect the repository.
3. Render will detect `render.yaml`, install `requirements.txt`, and start
  the service with Uvicorn.
4. Open the generated `onrender.com` URL. The health check is available at
  `/api/health`.

The service currently stores uploaded datasets and analyses in memory, so
they are cleared when the service restarts. This is suitable for the demo;
use persistent storage before treating it as a production application.

## Deploying the frontend on Cloudflare Pages

The frontend can also be deployed separately on Cloudflare Pages while the
FastAPI API remains on Render. The frontend is already configured to call
`https://fairlens.onrender.com/api`; change that URL in
`frontend/js/config.js` if Render assigns a different service URL.

In Cloudflare Pages, create a project from this GitHub repository with:

- **Framework preset:** None
- **Build command:** leave blank
- **Build output directory:** `frontend`

After the Pages deployment finishes, open the generated Pages URL. The
Render backend must be deployed first, and its CORS policy currently allows
the Pages frontend to call the API.

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/demo-dataset` | Loads/returns the bundled demo dataset + profile |
| POST | `/api/upload` | Upload a CSV file (multipart form, field `file`) |
| POST | `/api/analyze` | Run a fairness test: `dataset_id`, `protected_attribute`, `outcome_column`, `positive_outcome`, optional `ground_truth_column` |
| POST | `/api/simulate` | Educational mitigation simulation: `group_a_rate`, `group_b_rate` (0–1) |
| GET | `/api/report?dataset_id=...` | Downloads a plain-text report for the dataset's last analysis |

## Future improvements

- Persist datasets and analyses in a real database instead of in-memory
  storage (currently reset on server restart).
- Support additional fairness metrics (equalized odds, calibration).
- Allow selecting a separate ground-truth label column from the UI so
  equal opportunity (TPR) can be computed for more datasets.
- Add user accounts so students can save and compare multiple analyses.
- Export the report as PDF in addition to plain text.

## Disclaimer

> FairLens is an educational prototype designed to demonstrate concepts in
> AI fairness and bias detection. Its metrics and scoring should not be
> interpreted as legal, regulatory, medical, financial, or production-model
> certification.
