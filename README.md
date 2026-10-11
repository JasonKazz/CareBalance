# CareBalance

**Can this payment contract keep a community clinic running?** CareBalance compares per-visit and per-patient monthly payment offers, checks appointment capacity, and calculates feasible payment terms under a clinic margin target and insurer budget.

This is a working local planning prototype using synthetic inputs and simplified contracts. It does not predict clinical outcomes, establish fair prices, or replace professional contract analysis. No language model generates its numbers.

## Run

Python 3.9+; no packages, API keys, database, or build step required.

```sh
python3 backend/server.py
```

Open http://127.0.0.1:3200. Stop with Ctrl+C. This development server binds to localhost; it is not a production hosting setup.

## Demo in one minute

1. Load **Community clinic**. The per-patient offer produces $6,250 baseline surplus but loses $50 in the stress case. At a 5% margin target, feasible monthly per-patient rates are $40.04–$43.33 under the example budget.
2. Select **Demand outgrows capacity**. The clinic needs 765 appointments but has 650. Higher payment alone does not fix the 115-appointment gap.
3. Select **A budget too small**. Neither model satisfies all constraints.
4. Change assumptions, inspect formulas, or download the scenario and results as JSON.

The solver intersects exact rate intervals for baseline and stressed utilization, then rounds inward to cents. Its objective is minimum payer payment subject to modeled clinic margin, capacity, and payer-budget constraints. It reports no solution instead of inventing an optimum. Care delivery costs and insurer payments are separate quantities.

## Validation

```sh
python3 -m unittest discover -s tests -v
```

Tests cover hand-calculated examples, capacity failures, infeasible budgets, cent rounding and interval boundaries, deterministic results, input validation, API errors, and static-file access restrictions. Passing these checks validates implementation against the stated model, not real-world clinical or financial accuracy.

## Structure

- `frontend/`: accessible inputs, comparisons, SVG stress chart, formulas, JSON export.
- `backend/models/contracts.py`: pure monthly accounting functions.
- `backend/simulation/engine.py`: input validation, stress scenarios, analytical rate solver.
- `backend/server.py`: bounded local JSON API and static asset allowlist.
- `shared/`: explicit JSON request and result schemas.
- `data/synthetic/`: fictional clinic example.
- `tests/`: arithmetic and API checks.
- `docs/`: architecture and model assumptions.

`.env` is ignored and unused; no configuration or credentials are needed. `.env.example` documents that boundary. Inputs remain in the browser and local server memory; the application has no analytics, external API requests, or persistence. Use fictional data for this demo.

See [model assumptions](docs/model.md), [architecture](docs/architecture.md), and [diagram](docs/architecture.svg).
