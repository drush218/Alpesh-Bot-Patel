# Portfolio Terminal

A personal investment terminal I built to run my own stock portfolio. It pulls live holdings from my Trading212 account, compares them with my own earnings models for each company, and shows which positions need attention, either because the price has moved more than the market explains or because a model has gone stale after an earnings report.

It's deployed and I use it day to day.

<!-- Screenshots: add 2–3 images here (e.g. docs/dashboard.png, docs/analysis.png, docs/macro.png). Blur £ values first. -->

## Why I built it

I was tracking positions in Trading212, earnings models in spreadsheets and macro views in my head. None of it was connected, so I couldn't quickly answer *"is this stock still cheap on my numbers, and has anything changed since I last looked?"* This app puts all of it on one screen.

## What it does

| Screen | What it's for |
|---|---|
| **Dashboard** | Account value, net deposits and money-weighted return (XIRR) compared with the indices you'd have bought on the same dates; upcoming earnings and dividends |
| **Book** | Live holdings with allocation and P&L, concentration by index, and an *expected move* check: a regression against each stock's index flags moves the market doesn't explain (\|z\| ≥ 2.5) |
| **Analyses** | A screener of every stock I've modelled: forward PE, EPS growth, macro headwinds or tailwinds, and my own scorecard |
| **Analysis** | Per-stock earnings model (segment revenue → margin → EPS) with LOW/BASE/HIGH ranges, an editable scenario workspace, sensitivities and an implied share price; flags a model as stale once an earnings date passes after its data date |
| **Macro** | Live macro factor moves (FRED) mapped onto each holding's sensitivities, giving a net headwind or tailwind per stock and for the whole book |
| **Sizer** | Risk-first position sizing: how much to buy given a stop-loss and the maximum I'm willing to lose |

## How it's built

- **Backend:** Python, FastAPI. Thin routers and a service layer. Market data from Yahoo Finance and FRED, positions and cash flows from the Trading212 API (rate-limited and cached).
- **Frontend:** React and TypeScript (Vite), plain CSS design tokens.
- **Data:** Supabase (Postgres and Auth). Every request runs as the signed-in user, so row-level security protects personal data at the database level. Broker API keys are encrypted at rest (Fernet).
- **Models:** each analysis is a markdown file with an embedded JSON model. A parser validates it and writes it as a new version, so old analyses are kept and history is never overwritten.
- **Deployment:** one Docker image (FastAPI serving the API and the built frontend) on Render.
- **Tests:** unit tests for the parser, model engine, returns maths, expected-move check and API endpoints.

## How it evolved

- **v1 (Feb 2026):** a Streamlit app with a portfolio view, allocation chart and position-size calculator. Useful, but slow and hard to extend.
- **v1.x:** added deposit tracking from the Trading212 transaction history, true return on deposits and an encrypted credential store.
- **v2 (Oct 2026):** rebuilt as a proper web app (FastAPI and React) around stock models: the analysis workspace, the macro screen, the expected-move check and money-weighted returns compared with the indices.

I built it with AI coding tools (Claude Code), handling the product decisions, the data model and reviewing the work myself.

## Running locally

```bash
# backend
python -m venv backend/venv
backend/venv/Scripts/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env    # fill in Supabase URL/key and a Fernet key
backend/venv/Scripts/uvicorn app.main:app --app-dir backend --port 8000

# frontend
npm --prefix frontend ci
cp frontend/.env.example frontend/.env  # Supabase URL + publishable key
npm --prefix frontend run dev
```

Database schema: `supabase/migrations/`. Tests: `backend/venv/Scripts/python -m unittest discover -s tests`.
