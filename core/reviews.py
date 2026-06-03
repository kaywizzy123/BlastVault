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
            "id":                "20260530_101523_123456",
            "file_path":        "C:/SHOWS/.../char_hero_v012.mp4",
            "submitted_by":     "oogunremi",
            "submitted_at":     "2026-05-30T10:15:23",
            "submission_note":  "Ready for review",
            "priority":         "normal",   # "normal" | "high" | "urgent"
            "version":          1,          # increments each resubmission
            "review_status":    "",         # "" = pending | "Approved" | "Revision" | "On Hold"
            "reviewer_note":    "",
            "frame_annotations": [],        # [{start, end, note}]
            "reviewed_at":      "",
            "version_history":  []          # previous versions archived here
        }
    ]
}

``version_history`` entry schema
─────────────────────────────────
{
    "version":        1,
    "file_path":      "...",
    "submitted_at":   "...",
    "submission_note":"...",
    "review_status":  "Revision",
    "reviewer_note":  "...",
    "frame_annotations": [],
    "reviewed_at":    "..."
}

``frame_annotations`` entry schema
────────────────────────────────────
{
    "start": 24,
    "end":   48,
    "note":  "needs more overlap"
}

Session templates
─────────────────
Templates are stored in the catalog's .reviews/templates.json:
{
    "templates": [
        {
            "name":     "End of Day Dailies",
            "type":     "Director Dailies",
            "sequences": ["char", "bg"],
            "note":     "Standard daily check"
        }
    ]
}
"""
from __future__ import annotations

import json
import re
import datetime
from pathlib import Path

_REVIEWS_DIR   = ".reviews"
_TEMPLATES_FILE = "templates.json"

# Priority ordering for sorting (lower = higher priority in list)
PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "": 2}


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


def _shot_slug(file_path: str) -> str:
    """Version-agnostic shot identifier for re-submission matching.

    Strips trailing _vXXX / _V### from the filename stem and combines
    with the parent directory so two files are only considered the same
    shot when they share both folder and base name.

        SEQ_01/SHOT_01/char_hero_v001.mov  →  …/SHOT_01/char_hero
        SEQ_01/SHOT_01/char_hero_v002.mov  →  …/SHOT_01/char_hero  ← match
        SEQ_01/SHOT_02/char_hero_v001.mov  →  …/SHOT_02/char_hero  ← no match
    """
    p    = Path(file_path)
    stem = re.sub(r"_v\d+$", "", p.stem, flags=re.IGNORECASE)
    return str(p.parent / stem).lower()


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
        if f.name == _TEMPLATES_FILE:
            continue
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
    """Append or re-version submission items in an existing session.

    Each dict in *new_items* must have:
        file_path        str
        submitted_by     str
        submission_note  str   (may be "")
        priority         str   "normal" | "high" | "urgent"  (default "normal")

    Re-submission handling:
        If *file_path* already exists in the session, the previous item is
        archived to ``version_history`` and a new item is created with
        ``version`` incremented.  This preserves the review trail while
        surfacing the latest cut.
    """
    data     = read_session(session_path)
    now      = datetime.datetime.now().isoformat(timespec="seconds")

    # Build a lookup: version-slug → list index
    # This lets char_hero_v002.mov match an existing char_hero_v001.mov entry.
    items = data.setdefault("items", [])
    slug_idx: dict[str, int] = {
        _shot_slug(it["file_path"]): i for i, it in enumerate(items)
    }

    for item in new_items:
        fp       = item.get("file_path", "")
        priority = item.get("priority", "normal")
        if not fp:
            continue

        slug = _shot_slug(fp)

        if slug in slug_idx:
            # ── Re-submission: archive current, bump version ──────────────
            old      = items[slug_idx[slug]]
            old_ver  = old.get("version", 1)

            archive_entry = {
                "version":           old_ver,
                "file_path":         old.get("file_path", fp),
                "submitted_by":      old.get("submitted_by", ""),
                "submitted_at":      old.get("submitted_at", ""),
                "submission_note":   old.get("submission_note", ""),
                "priority":          old.get("priority", "normal"),
                "review_status":     old.get("review_status", ""),
                "reviewer_note":     old.get("reviewer_note", ""),
                "frame_annotations": old.get("frame_annotations", []),
                "reviewed_at":       old.get("reviewed_at", ""),
            }

            prev_history = old.get("version_history", [])

            items[slug_idx[slug]] = {
                "id":                _item_id(),
                "file_path":         fp,
                "submitted_by":      item.get("submitted_by", ""),
                "submitted_at":      now,
                "submission_note":   item.get("submission_note", ""),
                "priority":          priority,
                "version":           old_ver + 1,
                "review_status":     "",
                "reviewer_note":     "",
                "frame_annotations": [],
                "reviewed_at":       "",
                "version_history":   prev_history + [archive_entry],
            }
        else:
            # ── New submission ────────────────────────────────────────────
            new_item = {
                "id":                _item_id(),
                "file_path":         fp,
                "submitted_by":      item.get("submitted_by", ""),
                "submitted_at":      now,
                "submission_note":   item.get("submission_note", ""),
                "priority":          priority,
                "version":           1,
                "review_status":     "",
                "reviewer_note":     "",
                "frame_annotations": [],
                "reviewed_at":       "",
                "version_history":   [],
            }
            items.append(new_item)
            slug_idx[slug] = len(items) - 1

    # Sort items: urgent → high → normal, then by submitted_at
    items.sort(key=lambda x: (
        PRIORITY_ORDER.get(x.get("priority", "normal"), 2),
        x.get("submitted_at", ""),
    ))

    write_session(session_path, data)


def set_item_review(
    session_path: str | Path,
    item_id: str,
    review_status: str,
    reviewer_note: str,
    frame_annotations: list[dict] | None = None,
) -> None:
    """Set the review outcome for one item and write the session file."""
    data = read_session(session_path)
    now  = datetime.datetime.now().isoformat(timespec="seconds")
    for item in data.get("items", []):
        if item["id"] == item_id:
            item["review_status"]    = review_status
            item["reviewer_note"]    = reviewer_note
            item["frame_annotations"] = frame_annotations or []
            item["reviewed_at"]      = now if review_status else ""
            break
    write_session(session_path, data)


def set_item_priority(
    session_path: str | Path,
    item_id: str,
    priority: str,
) -> None:
    """Update the priority of a single item."""
    data = read_session(session_path)
    for item in data.get("items", []):
        if item["id"] == item_id:
            item["priority"] = priority
            break
    # Re-sort after priority change
    items = data.get("items", [])
    items.sort(key=lambda x: (
        PRIORITY_ORDER.get(x.get("priority", "normal"), 2),
        x.get("submitted_at", ""),
    ))
    write_session(session_path, data)


def batch_set_review(
    session_path: str | Path,
    item_ids: list[str],
    review_status: str,
    reviewer_note: str,
) -> None:
    """Set the same review status on multiple items at once."""
    data = read_session(session_path)
    now  = datetime.datetime.now().isoformat(timespec="seconds")
    id_set = set(item_ids)
    for item in data.get("items", []):
        if item["id"] in id_set:
            item["review_status"] = review_status
            item["reviewer_note"] = reviewer_note
            item["reviewed_at"]   = now if review_status else ""
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


# ── Session templates ─────────────────────────────────────────────────────── #

def _templates_path(catalog_root: str) -> Path:
    return get_reviews_dir(catalog_root) / _TEMPLATES_FILE


def list_templates(catalog_root: str) -> list[dict]:
    """Return saved session templates for *catalog_root*."""
    p = _templates_path(catalog_root)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("templates", [])
    except Exception:
        return []


def save_template(catalog_root: str, template: dict) -> None:
    """Save or replace a template by name."""
    p         = _templates_path(catalog_root)
    templates = list_templates(catalog_root)
    # Replace existing with same name
    templates = [t for t in templates if t.get("name") != template.get("name")]
    templates.append(template)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"templates": templates}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def delete_template(catalog_root: str, name: str) -> None:
    """Remove a template by name."""
    p         = _templates_path(catalog_root)
    templates = [t for t in list_templates(catalog_root) if t.get("name") != name]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"templates": templates}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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
