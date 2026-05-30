"""
Notes storage — per-asset review notes log.

Notes are keyed on the canonical base stem (version number stripped) so all
versions of the same asset share one notes file.  Storage location:
    <asset_folder>/.meta/<canonical_stem>.notes.json
"""
import json
import uuid
import datetime
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────── #
#  Internal helpers                                                              #
# ──────────────────────────────────────────────────────────────────────────── #

def _notes_path(file_path: Path) -> Path:
    """Return the .notes.json path for a given asset file.

    Keyed on the full stem (including version number) so each version
    has its own independent notes file.
    """
    return file_path.parent / ".meta" / f"{file_path.stem}.notes.json"


# ──────────────────────────────────────────────────────────────────────────── #
#  Public API                                                                    #
# ──────────────────────────────────────────────────────────────────────────── #

def read_notes(file_path) -> list:
    """Return all notes for *file_path* as a list of dicts (oldest first).
    Returns an empty list on any error or if no notes exist yet."""
    p = _notes_path(Path(file_path))
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def write_notes(file_path, notes: list) -> None:
    """Persist *notes* to disk for *file_path*."""
    p = _notes_path(Path(file_path))
    p.parent.mkdir(exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)


def add_note(file_path, author: str, content: str) -> dict:
    """Append a new note to *file_path* and return the new note dict."""
    notes = read_notes(file_path)
    note = {
        "id":      str(uuid.uuid4())[:8],
        "author":  author.strip(),
        "date":    datetime.datetime.now().isoformat(timespec="seconds"),
        "content": content.strip(),
    }
    notes.append(note)
    write_notes(file_path, notes)
    return note


def delete_note(file_path, note_id: str) -> None:
    """Remove the note with *note_id* from *file_path*'s notes list."""
    notes = read_notes(file_path)
    notes = [n for n in notes if n.get("id") != note_id]
    if notes:
        write_notes(file_path, notes)
    else:
        # No notes left — remove the file entirely so has_notes() returns False
        p = _notes_path(Path(file_path))
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


def has_notes(file_path) -> bool:
    """Return True if *file_path* has at least one note attached."""
    return _notes_path(Path(file_path)).exists()
