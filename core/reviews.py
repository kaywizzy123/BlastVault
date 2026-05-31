"""
core/reviews.py
───────────────
Review session management for BlastVault.

Sessions live in  CATALOG_ROOT/.reviews/  as dated JSON files:

    CATALOG_ROOT/
        .reviews/
            2026-05-30_director-dailies.json
            2026-05-29_hoa-rounds.json

Session JSON schema
-------------------
{
    "id":           "2026-05-30_director-dailies",
    "session_type": "Director Dailies",
    "date":         "2026-05-30",
    "created_at":   "2026-05-30T09:00:00",
    "status":       "open",        # "open" | "completed"
    "items": [
        {
            "id":              "20260530_101523_123456",
            "file_path":       "C:/SHOWS/.../char_hero_v012.mp4",
            "submitted_by":    "oogunremi",
            "submitted_at":    "2026-05-30T10:15:23",
            "submission_note": "Ready for review",
            "review_status":   "",   # "" = pending | STATUS_OPTIONS value
            "reviewer_note":   "",
            "reviewed_at":     ""
        }
    ]
}
"""
from __future__ import annotations

import json
import re
import datetime
from pathlib import Path

_REVIEWS_DIR = ".reviews"


# ── Path helpers ──────────────────────────────────────────────────────────── #

def get_reviews_dir(catalog_root: str) -> Path:
    """Return the .reviews folder path for *catalog_root*."""
    return Path(catalog_root) / _REVIEWS_DIR


def _slug(text: str) -> str:
    """'Director Dailies' → 'director-dailies'"""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _item_id() -> str:
    """Unique item ID based on current timestamp."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")


# ── CRUD ─────────────────────────────────────────────────────────────────── #

def list_sessions(catalog_root: str) -> list[dict]:
    """Return all sessions for *catalog_root*, newest first.

    Each entry is the parsed session dict with an extra ``'path'`` key
    pointing to the JSON file.
    """
    d = get_reviews_dir(catalog_root)
    if not d.exists():
        return []
    result = []
    for f in sorted(d.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["path"] = str(f)
            result.append(data)
        except Exception:
            pass
    return result


def read_session(session_path: str | Path) -> dict:
    """Read and return a session dict, or ``{}`` on error."""
    try:
        return json.loads(Path(session_path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_session(session_path: str | Path, data: dict) -> None:
    """Write *data* to *session_path*, creating parent dirs as needed."""
    p = Path(session_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def create_session(catalog_root: str, session_type: str) -> str:
    """Create a new open session for today and return its file path.

    If a session of this type already exists today, returns the existing path
    rather than creating a duplicate.
    """
    today = datetime.date.today().isoformat()
    fname = f"{today}_{_slug(session_type)}"
    path  = get_reviews_dir(catalog_root) / f"{fname}.json"
    if path.exists():
        return str(path)
    data = {
        "id":           fname,
        "session_type": session_type,
        "date":         today,
        "created_at":   datetime.datetime.now().isoformat(timespec="seconds"),
        "status":       "open",
        "items":        [],
    }
    write_session(path, data)
    return str(path)


def add_items(session_path: str | Path, new_items: list[dict]) -> None:
    """Append submission items to an existing session.

    Each dict in *new_items* must have:
        file_path        str
        submitted_by     str
        submission_note  str (may be "")

    Duplicate file paths (same shot already in the session) are skipped.
    """
    data     = read_session(session_path)
    now      = datetime.datetime.now().isoformat(timespec="seconds")
    existing = {it["file_path"] for it in data.get("items", [])}

    for item in new_items:
        fp = item.get("file_path", "")
        if not fp or fp in existing:
            continue
        data.setdefault("items", []).append({
            "id":              _item_id(),
            "file_path":       fp,
            "submitted_by":    item.get("submitted_by", ""),
            "submitted_at":    now,
            "submission_note": item.get("submission_note", ""),
            "review_status":   "",
            "reviewer_note":   "",
            "reviewed_at":     "",
        })
        existing.add(fp)

    write_session(session_path, data)


def set_item_review(
    session_path: str | Path,
    item_id: str,
    review_status: str,
    reviewer_note: str,
) -> None:
    """Set the review outcome for one item and write the session file."""
    data = read_session(session_path)
    now  = datetime.datetime.now().isoformat(timespec="seconds")
    for item in data.get("items", []):
        if item["id"] == item_id:
            item["review_status"] = review_status
            item["reviewer_note"] = reviewer_note
            item["reviewed_at"]   = now if review_status else ""
            break
    write_session(session_path, data)


def mark_completed(session_path: str | Path) -> None:
    """Mark *session_path* as completed."""
    data = read_session(session_path)
    data["status"] = "completed"
    write_session(session_path, data)


def reopen_session(session_path: str | Path) -> None:
    """Reopen a completed session by setting its status back to 'open'."""
    data = read_session(session_path)
    data["status"] = "open"
    write_session(session_path, data)


def delete_session(session_path: str | Path) -> None:
    """Permanently delete the session JSON file."""
    try:
        Path(session_path).unlink(missing_ok=True)
    except Exception:
        pass


# ── Catalog helpers ───────────────────────────────────────────────────────── #

def find_catalog_root(file_path: str, catalog_roots: list[str]) -> str | None:
    """Return the catalog root in *catalog_roots* that contains *file_path*.

    Works for both file paths and directory paths.
    Returns ``None`` when no match is found.
    """
    p = Path(file_path).resolve()
    for root in catalog_roots:
        try:
            p.relative_to(Path(root).resolve())
            return root
        except ValueError:
            continue
    return None
