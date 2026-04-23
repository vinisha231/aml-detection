# AML Detection System

> An end-to-end Anti-Money Laundering (AML) detection platform built for analysts.
> Generates realistic synthetic transaction data, runs rules-based and graph-based
> detection, scores every account 0–100, and surfaces evidence in a React dashboard.

---

## What this project does (in plain English)

Banks are legally required to monitor for money laundering — criminals disguising
dirty money as legitimate transactions. This system:

1. **Generates fake but realistic bank data** — 5,000 accounts, 100,000 transactions,
   including known "dirty" patterns (money laundering typologies) mixed with everyday
   transactions (groceries, rent, salary).

2. **Runs two types of detection:**
   - *Rules engine* — Python functions that flag specific red flags (e.g., many deposits
     just under $10,000 = structuring).
   - *Graph signals* — treats accounts as nodes in a network, finds clusters, cycles,
     and high-centrality accounts using the NetworkX library.

3. **Scores every account 0–100** with an evidence string explaining WHY it scored high.

4. **Shows results in a dashboard** — analysts see a risk queue, click into accounts,
   and can "escalate to SAR" (Suspicious Activity Report) or dismiss false positives.

---

## Project structure

```
AMLDetector/
├── read/               ← READING MATERIALS (start here before coding)
├── backend/
│   ├── generator/      ← Synthetic data generator
│   ├── detection/      ← Rules + graph signals + scoring
│   ├── api/            ← FastAPI REST API
│   ├── database/       ← SQLite schema + queries
│   └── pipeline.py     ← Master script: generate → detect → score
├── frontend/           ← React dashboard
├── scripts/            ← CLI tools (generate data, run detection, evaluate)
└── data/               ← SQLite database lives here (git-ignored)
```

---

## Quick start

```bash
# 1. Install Python dependencies
cd backend
pip install -r requirements.txt

# 2. Generate 100k synthetic transactions
python ../scripts/generate_data.py

# 3. Run detection pipeline
python ../scripts/run_detection.py

# 4. See top-20 risky accounts
python pipeline.py --top 20

# 5. Start the API
uvicorn api.main:app --reload

# 6. Start the React dashboard (separate terminal)
cd ../frontend
npm install && npm run dev
```

---

## Typologies detected

| # | Name | Description | Detection method |
|---|------|-------------|-----------------|
| 1 | Structuring | Deposits just under $10k to avoid reporting | Rules: sub-threshold clustering |
| 2 | Layering | Funds hop through 3+ accounts quickly | Graph: chain detection |
| 3 | Funnel accounts | Many→few transaction pattern | Rules: fan-in/fan-out ratio |
| 4 | Round-tripping | Money leaves and returns same account | Graph: cycle detection |
| 5 | Shell clusters | Small groups transacting only with each other | Graph: community detection |
| 6 | Velocity anomalies | Dormant account suddenly very active | Rules: z-score vs baseline |

---

## Reading materials

See the `read/` folder for:
- FinCEN SAR guidance notes
- FATF typology summaries
- AML fundamentals
- Graph theory basics
- NetworkX tutorial

---

## Methodology

Detection combines two signal types scored 0–100 each, then weighted:

```
Final Risk Score = Σ (signal_score × signal_weight) / Σ weights
```

Evidence strings explain every score. Example output:
```
Account #A1042 | Risk: 91/100
  ✗ STRUCTURING: 12 deposits avg $9,640 across 9 days (conf: 87%)
  ✗ VELOCITY:    Tx count 47× above 30-day baseline (conf: 95%)
  ✓ GRAPH-PR:    PageRank 0.0089 — top 2% of all accounts
```

---

## Evaluation

The generator knows ground truth (which accounts are dirty). After running detection:

```bash
python scripts/evaluate.py
```

Outputs: Precision@20, Recall@100, False Positive Rate per rule.

---

* All data is synthetic. No real financial data used.*
