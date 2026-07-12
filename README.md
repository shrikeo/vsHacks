# Wishlist Price Checker

An AI-powered web app that tracks prices for your wishlist. Add any item and the
server uses **Google Gemini** (with `google_search` grounding) to fetch a current
market price, flag whether it's a **good deal**, and keep a running **total** of
what you'd spend. Prices auto-refresh in the background.

Built with **FastAPI** and **Google Gemini**. No database, no auth — items live
in memory for the demo.

## Features

- Current market price per item, pulled via Gemini search grounding
- "Good deal" badge when now looks like a good time to buy
- Running total of estimated spend across your wishlist
- Automatic background refresh every 60s
- Simple single-page web UI (daisyUI)

## Prerequisites

- Python 3.9+
- A Google Gemini API key — get one free at https://aistudio.google.com/apikey

## Setup

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd python_hackathon

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r fastapi/requirements.txt

# 4. Configure your API key
cp .env.example .env
# then edit .env and set GEMINI_API_KEY=<your key>
```

## Run

```bash
cd fastapi
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 in your browser (API docs at `/docs`).

| Method | Route | Description |
|--------|-------|-------------|
| GET    | `/` | Demo web page |
| GET    | `/api/items` | List items + running `total` |
| POST   | `/api/items` | Add an item (checks its price immediately) |
| POST   | `/api/check-prices` | Re-check all prices now |
| DELETE | `/api/items/{id}` | Remove an item |
| GET    | `/health` | Health check (returns 200) |

## How it works

```
Add item ─► Gemini (google_search grounding) ─► price + good deal? + note
Background loop (every 60s) ─► re-checks all prices
UI ─► shows each item, a deal badge, and the estimated total to pay
```

## Project structure

```
python_hackathon/
├── README.md
├── .env.example          # copy to .env and add your key
└── fastapi/
    ├── main.py           # FastAPI app, in-memory items, background automation, UI
    ├── price_service.py  # Gemini price lookup (Google Search grounding)
    ├── requirements.txt
    └── Dockerfile        # optional: containerized deploy
```

## Docker (optional)

The app listens on port `8080` in the container and exposes `GET /health`.

```bash
cd fastapi
docker build -t wishlist-price-checker .
docker run -p 8080:8080 --env-file ../.env wishlist-price-checker
# open http://127.0.0.1:8080
```

## Notes

- Gemini returns a representative market price, not one specific store's checkout
  price — good for a demo. Use a dedicated price API for exact live prices.
- The background refresh interval is `CHECK_INTERVAL_SECONDS` in `main.py`.
