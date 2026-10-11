# CareBalance

An interactive healthcare payment simulator using explicit, synthetic assumptions.

**Status:** repository scaffold only. The frontend and backend health endpoint work; payment calculations, optimization, charts, and outcome prediction are not implemented.

## Run locally

Requires Python 3.9 or newer. No dependencies or API keys required.

```sh
python3 backend/server.py
```

Open http://127.0.0.1:3200. Stop with Ctrl+C.

## Structure

```text
frontend/             HTML, CSS, JavaScript controls and charts
backend/server.py     Local HTTP server and health endpoint
backend/models/       Planned pure payment-contract calculations
backend/simulation/   Planned scenario evaluation and bounded search
shared/               Planned request/result JSON schemas
data/synthetic/      Planned clearly labeled illustrative inputs
tests/               Planned arithmetic and accounting checks
docs/                Architecture and scope
.env.example          Placeholder configuration only
.env                  Ignored local configuration
```

## First demo scope

One fictional hospital, one insurer, one episode of care. Compare simplified fee-for-service, bundled payment, and shared-savings contracts against the same patient scenarios. Show provider costs, provider margin, insurer payments, and sensitivity to assumed complications. Search payment terms under explicit constraints; report when none are feasible.

Payment changes do not automatically change complication rates. Clinical outcomes are assumptions, not predictions. Lower payments can redistribute financial risk without reducing care delivery costs. No real patient data, live claims ingestion, database, or LLM is required.

See [architecture](docs/architecture.md) and the [diagram](docs/architecture.svg).
