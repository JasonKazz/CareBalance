# CareBalance — Contract Lens

See what a proposed payment schedule would mean for the services a community clinic actually delivers.

Upload a text-based contract PDF or text offer, review extracted rates against source passages, and reprice an aggregate annual service CSV. The frontend shows service-level contributions, matched-volume coverage, a counteroffer slider, and an exportable audit trail. The earlier capacity and payment-model calculator remains available at `/clinic`.

## Run locally

Python 3.10+ recommended (tested on 3.12). One dependency: pypdf for local PDF text reading.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python backend/server.py
```

Open http://127.0.0.1:3200. Stop with Ctrl+C. Local development server only; not a production deployment.

## Optional Gemini extraction

Place `GEMINI_API_KEY=your_key` in ignored `.env`. Do not commit it. Config is loaded for each request; reload the page after adding a key. Choose Gemini and acknowledge the disclosure to send extracted contract text to Google. The CSV stays local to the app. No app-side document persistence, analytics, or request-body logging. Provider processing/retention is separate from app storage. Use public or fictional documents for this demo.

The adapter uses `gemini-3.8-flash`, low thinking, structured output, one request with a 25-second socket timeout, no automatic retries, and at most two concurrent extractions. Old `gemini-2.5-flash` was rejected by the tested account. Rates still require human review. Token-based cost estimates use Google's published introductory prices through December 2026 and the announced rates afterward; actual billing can differ. See [provider notes](docs/provider-benchmark.md).

Without a key, the local parser reads only explicit `CODE | DESCRIPTION | USD RATE` rows. It does not interpret general contract language. The sample button actually parses the fictional offer, then waits for confirmation before repricing.

## Input scope

- Contracts: PDF/TXT, up to 4 MB, 20 pages, 60,000 extracted characters, 200 rate candidates. Scanned/image-only and encrypted PDFs are unsupported. A citation refers to extracted page text, not a visual PDF annotation.
- Activity: UTF-8 CSV, at most 500,000 characters and 1,000 rows, exact headers `code,description,annual_volume,current_rate`. One aggregated row per exact code; duplicate codes rejected. Annual volumes are nonnegative integers. Rates are nonnegative USD with at most two decimals. Zero rates are valid.
- Exact codes include any supplied modifiers. No modifier inference, Medicare multiplier resolution, bonus calculation, or automatic contract applicability determination.
- Duplicate contract alternatives are flagged and unselected. Unsupported source quotes are unselected. Users explicitly select and confirm rates before calculation; corrections are marked as user edits.

## Demo

1. Click **Explore a sample comparison**.
2. Open a **Page 1** evidence link, inspect the offer, and confirm the selected rates.
3. Compare: current matched reimbursement **$613,500**, proposed **$587,800**, difference **−$25,700**. One code is unmatched and excluded from both sides of the comparison.
4. Raise the hypothetical uniform uplift to **5%**: modeled reimbursement becomes **$617,190**, a **$3,690** increase versus current. Source rates remain unchanged.
5. Export the analysis or try your own supported fictional offer and CSV.

These are illustrative figures, not a real clinic's finances. Historical volumes are held constant. Outputs represent modeled fee-schedule reimbursement, not profit, actual collections, health outcomes, or advice to sign an agreement.

## Verify

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check frontend/app.js
```

A separate real-provider benchmark is available at `scripts/benchmark_extraction.py`; it requires a key and incurs API usage. Automated tests use local fixtures and mocked provider responses only.

## Architecture

- `frontend/`: Contract Lens UI and separate original capacity planner.
- `backend/documents/`: bounded PDF/text reading and source-presence checks.
- `backend/providers/gemini.py`: optional extraction only; never computes impact.
- `backend/repricing.py`: CSV validation, exact code matching, Decimal arithmetic, counteroffer calculations.
- `backend/config.py`: single credential/configuration loader.
- `backend/models/` and `backend/simulation/`: original capacity model.
- `data/synthetic/`: clearly fictional offer and aggregate activity examples.
- `tests/`: arithmetic, malformed inputs, PDF, evidence and API checks.

See [architecture](docs/architecture.md), [repricing model](docs/repricing.md), and [capacity assumptions](docs/model.md).
