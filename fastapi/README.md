# Wishlist Price Checker

A tiny FastAPI demo that shows **automation with Gemini**: add items to a
wishlist, and the server uses the Gemini API (with Google Search grounding) to
fetch a current price and flag good deals. Prices refresh automatically in the
background, and a running total shows what you'd spend.

No database, no auth — items live in memory for the demo.

## Run

```bash
pip install -r requirements.txt

# Gemini key (read from a .env file or the environment)
export GEMINI_API_KEY=your-key

uvicorn main:app --reload
```

Open **http://localhost:8000** — API docs at `/docs`.

## How it works

```
Add item ─► Gemini (google_search grounding) ─► price + good deal? + note
Background loop (every 60s) ─► re-checks all prices
UI ─► shows each item, a deal badge, and the estimated total to pay
```

## API

| Method | Route | Purpose |
|--------|-------|---------|
| GET  | `/` | Demo page (daisyUI) |
| GET  | `/health` | Health check |
| GET  | `/api/items` | List items + `total` spend |
| POST | `/api/items` | Add an item (checks its price immediately) |
| POST | `/api/check-prices` | Re-check all prices now |
| DELETE | `/api/items/{id}` | Remove an item |

## Files

- `main.py` — FastAPI app, in-memory items, background automation, demo page
- `price_service.py` — Gemini price lookup (Google Search grounding)
- `Dockerfile` — container image (serves on port 8080)

## Notes

- Gemini returns a representative market price, not one specific store's checkout
  price — good for a demo. Use a dedicated price API for exact live prices.
- The background interval is `CHECK_INTERVAL_SECONDS` in `main.py`.
