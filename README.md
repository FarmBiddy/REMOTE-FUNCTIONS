# Farm cost and revenue functions

Small calculation library extracted from the Dairy Financials prototype. It only covers the basic annual P&L: **revenue, costs, profit, and margin**.

Functions take explicit numbers. They do not read a database. A sample JSON is used now so the formulas can be checked; a platform loader can replace that later.

## Contract

Every call returns one of:

```json
{ "status": "ok", "function": "revenue.milk", "result": { "amount": 200000, "currency": "EUR" } }
```

```json
{
  "status": "needs_input",
  "function": "revenue.milk",
  "missing": [{ "field": "milk_price", "unit": "EUR/litre" }],
  "provided": ["milking_cows", "litres_per_cow"]
}
```

Missing inputs are listed with field name and unit. They are never guessed. Extra / unknown fields are rejected (`error`). Explicit `0` is valid; `null` and negatives are invalid. Full contract: [`docs/api-contract.md`](docs/api-contract.md).

Units: **EUR**, **annual**. `profit.margin` returns a 0–1 `margin` and a `margin_pct`. Published money and margins use **banker's rounding** (round half to even; ADR-0005).

## Functions

Keys in this table are **stable public calculation IDs** (not Python function names). Integrations must use these IDs. Catalogue: `farm_functions/registry.py`.

| Calculation ID | Required inputs | Formula |
|----------------|-----------------|---------|
| `revenue.milk` | `milking_cows`, `litres_per_cow`, `milk_price` | cows × litres × price |
| `revenue.schemes` | — | BISS + ACRES + other grants |
| `revenue.other` | — | cattle + lamb + wool + other |
| `revenue.total` | milk fields | milk + schemes + other |
| `costs.total` | — | sum of the 9 cost lines (missing = 0) |
| `profit.net` | `revenue`, `costs` | revenue − costs |
| `profit.margin` | `revenue`, `costs` | (revenue − costs) / revenue |
| `pl.summary` | milk fields | full P&L from raw drivers |

`profit.net` and `profit.margin` expect **already totalled** revenue and costs. Use `pl.summary` when you still have the raw farm numbers.

## Sample farm (`sample_data/farm.json`)

| Line | Amount |
|------|--------|
| Milk (100 × 5000 × €0.40) | €200,000 |
| Schemes | €25,000 |
| Cattle sales | €15,000 |
| **Revenue** | **€240,000** |
| **Costs** | **€175,000** |
| **Profit** | **€65,000** |
| **Margin** | **27.08%** |

## Run

Use a named local venv (prompt style `remote-functions`). Do not commit `.venv/`.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

**Windows cmd**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pytest
```

**Unix**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
```

**API**

- Non-reload (process entry): `python run_server.py`
- Local reload: `python -m uvicorn api.app:app --reload` (or `start.bat` on Windows)

On Windows, use `python -m uvicorn` (the bare `uvicorn` command is often not on PATH). Keep that terminal open, then call the API from another terminal or open http://127.0.0.1:8000/docs.

- `GET /livez` — liveness
- `GET /health` — liveness alias
- `GET /v1/functions` — discovery
- `POST /v1/functions/<key>/run` — one typed route per function (e.g. `revenue.milk`); body is a JSON object of numbers; OpenAPI shows the real field names
- `POST /v1/demo/pl-summary` — runs `pl.summary` on the sample farm
- OpenAPI: `http://127.0.0.1:8000/docs`

## Out of scope

KPIs (feed ratio, per cow), monthly cashflow, Monte Carlo, alerts, risk, and farm-file loading from Dairy Financials.

## Docs

- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Domain model: [`docs/domain-model.md`](docs/domain-model.md)
- Development: [`docs/development.md`](docs/development.md)
- Delivery bootstrap (execute here): [`docs/delivery-bootstrap.md`](docs/delivery-bootstrap.md)
- API contract: [`docs/api-contract.md`](docs/api-contract.md)
- Decisions (ADRs): [`docs/decisions/`](docs/decisions/)

