import os
import json
from typing import Optional, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ITEMS_FILE = os.path.join(DATA_DIR, "items_store.json")
SEQS_FILE = os.path.join(DATA_DIR, "sequences.json")

os.makedirs(DATA_DIR, exist_ok=True)

# in-memory caches loaded from disk
_items = {}
_seqs = {}

def _load():
    global _items, _seqs
    try:
        if os.path.exists(ITEMS_FILE):
            with open(ITEMS_FILE, "r", encoding="utf-8") as f:
                _items = json.load(f)
    except Exception:
        _items = {}
    try:
        if os.path.exists(SEQS_FILE):
            with open(SEQS_FILE, "r", encoding="utf-8") as f:
                _seqs = json.load(f)
    except Exception:
        _seqs = {}

_load()


def save_item(item_id: str, item: Dict[str, Any]):
    _items[item_id] = item
    with open(ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(_items, f, indent=2)


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    return _items.get(item_id)


def delete_item(item_id: str):
    if item_id in _items:
        del _items[item_id]
        with open(ITEMS_FILE, "w", encoding="utf-8") as f:
            json.dump(_items, f, indent=2)


def get_next_sequence(item_id: str, entity: str) -> int:
    key = f"{item_id}::{entity}"
    seq = _seqs.get(key, 1)
    return seq


def increment_sequence(item_id: str, entity: str):
    key = f"{item_id}::{entity}"
    seq = _seqs.get(key, 1)
    _seqs[key] = seq + 1
    with open(SEQS_FILE, "w", encoding="utf-8") as f:
        json.dump(_seqs, f, indent=2)


# expose a simple storage object for import convenience
class _Storage:
    save_item = staticmethod(save_item)
    get_item = staticmethod(get_item)
    delete_item = staticmethod(delete_item)
    get_next_sequence = staticmethod(get_next_sequence)
    increment_sequence = staticmethod(increment_sequence)

storage = _Storage()
