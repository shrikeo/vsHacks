"""Wishlist price checker — FastAPI + Gemini demo (JSON-file persisted, per-user)."""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from price_service import priceClient

CHECK_INTERVAL_SECONDS = 60  # demo: refresh every minute (use 86400 for once-a-day in prod)
INDEX_HTML = Path(__file__).parent / "index.html"
DB_FILE = Path(__file__).parent / "db.json"

# Each user's wishlist is just a list of items, keyed by name: { "Khoa": [ {item}, ... ] }
users: dict[str, list[dict]] = {}


class ItemIn(BaseModel):
    name: str


def _load_db() -> None:
    # Restore every user's wishlist from db.json on startup.
    global users
    if not DB_FILE.exists():
        return
    try:
        users = json.loads(DB_FILE.read_text())
    except (json.JSONDecodeError, OSError) as error:
        print(f"could not read {DB_FILE.name}: {error}")


def _save_db() -> None:
    # Persist all wishlists so they survive restarts. Atomic-ish write.
    tmp = DB_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(users, indent=2))
    tmp.replace(DB_FILE)


def _wishlist(user: str) -> list[dict]:
    # Look up (or create) a user's list of items by name.
    return users.setdefault(user.strip(), [])


def _next_id(items: list[dict]) -> int:
    return max((i["id"] for i in items), default=0) + 1


def _apply_price(item: dict, result: dict) -> None:
    item["price"] = result.get("price")
    item["good_deal"] = bool(result.get("goodDeal", False))
    item["note"] = result.get("note", "")
    item["sources"] = result.get("sources", [])
    item["status"] = "done"
    item["checked_at"] = datetime.now(timezone.utc).isoformat()


async def _check_one(item: dict) -> None:
    # check_price is a blocking SDK call, so run it off the event loop.
    item["status"] = "checking"
    try:
        _apply_price(item, await asyncio.to_thread(priceClient.check_price, item["name"]))
    except Exception as error:
        print(f"price check failed for {item['name']}: {error}")
        # Mark it failed so the UI stops spinning/polling and shows why.
        item["status"] = "error"
        if "429" in str(error) or "RESOURCE_EXHAUSTED" in str(error):
            item["note"] = "Gemini free-tier limit reached — try again in a minute."
        else:
            item["note"] = "Couldn't fetch price right now — try again shortly."


async def _refresh(items: list[dict]) -> None:
    for item in items:
        await _check_one(item)


async def interval_check_price() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        for items in users.values():
            if items:
                await _refresh(items)
        _save_db()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_db()
    task = asyncio.create_task(interval_check_price())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    # Required by AgentBase Runtime.
    return {"status": "ok"}


@app.get("/api/items")
def list_items(user: str):
    items = _wishlist(user)
    total = round(sum(i["price"] or 0 for i in items), 2)
    return {"items": items, "total": total}


async def _check_and_save(item: dict) -> None:
    await _check_one(item)
    _save_db()


@app.post("/api/items")
async def add_item(item: ItemIn, user: str):
    items = _wishlist(user)
    record = {"id": _next_id(items), "name": item.name, "price": None, "good_deal": False, "note": "", "sources": [], "status": "checking"}
    items.append(record)
    _save_db()
    # Fetch the price in the background so the item shows up instantly.
    asyncio.create_task(_check_and_save(record))
    return record


@app.post("/api/check-prices")
async def check_prices(user: str):
    items = _wishlist(user)
    await _refresh(items)
    _save_db()
    return {"checked": len(items)}


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, user: str):
    items = _wishlist(user)
    items[:] = [i for i in items if i["id"] != item_id]
    _save_db()
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(INDEX_HTML)
