# Ageing Futures – Streamlit Edition

Ageing Futures is a competitive ageing-policy simulation designed for Masters of Public Health programmes.
Lecturers create game sessions with configurable horizons, budgets, and scoring weights. Ten or more teams join
using a shared room code, select policy mixes within their budgets, and compete across health, cost, capacity,
and equity objectives while shocks and capacity constraints shape outcomes.

This repository delivers a production-ready Streamlit application backed by SQLite/SQLModel with a modular
simulation engine, visual analytics, printable materials, and export tools.

## Repository Structure

```
.
├── ageing_futures/
│   ├── config/              # JSON configuration bundles and UK regions GeoJSON
│   ├── db/                  # SQLModel models, CRUD helpers, cached DB connection
│   ├── sim/                 # Simulation engine, policies, shocks, scoring, baseline generator
│   └── viz/                 # Plotly and PyDeck helpers
├── streamlit_app/
│   ├── Home.py              # Landing page
│   └── pages/               # Streamlit multipage workflow (join, dashboard, policies, etc.)
├── tests/                   # Pytest unit tests for engine, policies, scoring
├── .streamlit/config.toml   # Streamlit theme configuration
├── requirements.txt         # Pinned dependency versions (Streamlit compatible)
└── README.md
```

## Quick Start

1. **Install dependencies** (Python 3.10+ recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Launch the app locally**:

   ```bash
   streamlit run streamlit_app/Home.py
   ```

   The app defaults to using a SQLite database (`ageing_futures.db`) in the project root. Override the database
   by setting `DATABASE_URL` (e.g. a PostgreSQL connection string) before launching Streamlit.

3. **Create a session** from the “Join or Create Session” page, share the room code with teams, and have each team
   join to receive a personalised dashboard and policy workspace.

4. **Advance rounds** via the Lecturer Console:
   - Create a round and optional shock card.
   - Teams lock in their policy mixes.
   - Click **Advance round** to run the simulation for the configured number of months. The console
     persists cohort state, stores metrics and time series in SQL, and refreshes dashboards + leaderboard automatically.

5. **Export results** from the Exports page for per-team summaries and detailed monthly time series.

## Configuration

Configuration files live in `ageing_futures/config/` and are validated using Pydantic models:

- `baseline_population_config.json` – cohort size, demographic distributions, service indices.
- `transitions_config.json` – monthly hazard models, coefficients, and length-of-stay parameters.
- `policies_config.json` – policy library with costs, effect sizes, lags, and diminishing returns.
- `costs_config.json` – unit costs (beds, care home, community) and QALY weights.
- `scoring_config.json` – default scoring weights and equity dimensions.
- `regions_uk.geojson` – lightweight UK region polygons for PyDeck maps.

Update these files to reflect new evidence; changes take effect on app restart. Session-level overrides for
cohort size and scoring weights are supported via the Lecturer Console when creating sessions.

## Tests

Execute unit tests with:

```bash
pytest
```

Tests cover the simulation engine, policy cost/effect aggregation, and scoring normalisation to ensure
core mechanics remain stable.

## Deployment

The application is Streamlit Community Cloud ready:

- Push this repository to GitHub.
- In Streamlit Cloud, deploy `streamlit_app/Home.py` and add the `DATABASE_URL` secret if you are using
  a managed Postgres instance.
- Dependencies are fully specified in `requirements.txt`; no extra build steps are required.

## Printables

The “Printables” page renders policy and shock cards as PNG downloads complete with QR codes linking back
into the relevant app views. Cards use an accessible, high-contrast palette suitable for tabletop exercises.

---

Licensed under the MIT License.
