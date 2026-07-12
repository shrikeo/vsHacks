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

# Each user has their own wishlist, keyed by name: { name: {"items": [...], "next_id": N} }
users: dict[str, dict] = {}


class ItemIn(BaseModel):
    name: str


def _load_db() -> None:
    # Restore every user's wishlist from db.json on startup.
    global users
    if not DB_FILE.exists():
        return
    try:
        users = json.loads(DB_FILE.read_text()).get("users", {})
    except (json.JSONDecodeError, OSError) as error:
        print(f"could not read {DB_FILE.name}: {error}")


def _save_db() -> None:
    # Persist all wishlists so they survive restarts. Atomic-ish write.
    tmp = DB_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"users": users}, indent=2))
    tmp.replace(DB_FILE)


def _wishlist(user: str) -> dict:
    # Look up (or create) a user's wishlist by name.
    name = user.strip()
    return users.setdefault(name, {"items": [], "next_id": 1})


def _apply_price(item: dict, result: dict) -> None:
    item["price"] = result.get("price")
    item["good_deal"] = bool(result.get("goodDeal", False))
    item["note"] = result.get("note", "")
    item["sources"] = result.get("sources", [])
    item["checked_at"] = datetime.now(timezone.utc).isoformat()


async def _check_one(item: dict) -> None:
    # check_price is a blocking SDK call, so run it off the event loop.
    try:
        _apply_price(item, await asyncio.to_thread(priceClient.check_price, item["name"]))
    except Exception as error:
        print(f"price check failed for {item['name']}: {error}")


async def _refresh(items: list[dict]) -> None:
    for item in items:
        await _check_one(item)


async def interval_check_price() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        for wl in users.values():
            if wl["items"]:
                await _refresh(wl["items"])
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
    items = _wishlist(user)["items"]
    total = round(sum(i["price"] or 0 for i in items), 2)
    return {"items": items, "total": total}


async def _check_and_save(item: dict) -> None:
    await _check_one(item)
    _save_db()


@app.post("/api/items")
async def add_item(item: ItemIn, user: str):
    wl = _wishlist(user)
    record = {"id": wl["next_id"], "name": item.name, "price": None, "good_deal": False, "note": "", "sources": []}
    wl["next_id"] += 1
    wl["items"].append(record)
    _save_db()
    # Fetch the price in the background so the item shows up instantly.
    asyncio.create_task(_check_and_save(record))
    return record


@app.post("/api/check-prices")
async def check_prices(user: str):
    wl = _wishlist(user)
    await _refresh(wl["items"])
    _save_db()
    return {"checked": len(wl["items"])}


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, user: str):
    wl = _wishlist(user)
    wl["items"] = [i for i in wl["items"] if i["id"] != item_id]
    _save_db()
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(INDEX_HTML)
