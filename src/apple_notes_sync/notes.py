"""Apple Notes integration — native checklists via protobuf + HTML fallback."""

import gzip
import sqlite3
import uuid
from pathlib import Path

from apple_notes_sync.protobuf import field_bytes, field_str, field_varint
from apple_notes_sync.reminders import _run as _osascript

NOTES_DB = (
    Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
)

# Sentinel value used in CRDT to mark end-of-runs (max uint32)
_SENTINEL = 0xFFFFFFFF

# Apple Notes paragraph styles
_STYLE_TITLE = 0
_STYLE_HEADING = 1
_STYLE_TODO = 103


# --- Protobuf builders ---


def _build_f3_run(
    replica_id: int,
    pos: int,
    length: int,
    replica_id2: int,
    pos2: int,
    seq: int,
) -> bytes:
    """Build an f3 (CRDT text run) entry."""
    f1 = field_bytes(1, field_varint(1, replica_id) + field_varint(2, pos))
    f2 = field_varint(2, length)
    f3 = field_bytes(3, field_varint(1, replica_id2) + field_varint(2, pos2))
    return f1 + f2 + f3 + field_varint(5, seq)


def _build_f3_sentinel() -> bytes:
    """Build the sentinel f3 entry that marks end of runs."""
    f1 = field_bytes(1, field_varint(1, 0) + field_varint(2, _SENTINEL))
    f2 = field_varint(2, 0)
    f3 = field_bytes(3, field_varint(1, 0) + field_varint(2, _SENTINEL))
    return f1 + f2 + f3


def _build_f5(length: int, style: int, done: bool | None = None) -> bytes:
    """Build an f5 paragraph entry. See the _STYLE_* constants."""
    para = field_varint(1, style) + field_varint(3, 1)
    if done is not None:
        todo_msg = field_bytes(1, uuid.uuid4().bytes) + field_varint(2, int(done))
        para += field_bytes(5, todo_msg)
    return field_varint(1, length) + field_bytes(2, para)


def _build_f4(replica_uuid: bytes, text_len: int, para_count: int) -> bytes:
    """Build f4 replica metadata."""
    inner = field_bytes(1, replica_uuid)
    inner += field_bytes(2, field_varint(1, text_len))
    inner += field_bytes(2, field_varint(1, para_count))
    return field_bytes(1, inner)


def build_note_protobuf(title: str, sections: list[dict]) -> bytes:
    """Build complete Note protobuf with native checklists.

    sections: [{"heading": str, "tasks": [{"text": str, "completed": bool}]}]
    Returns gzipped protobuf ready for ZDATA.
    """
    replica_uuid = uuid.uuid4().bytes

    lines = [title]
    f5_entries = [_build_f5(len(title) + 1, style=_STYLE_TITLE)]

    for section in sections:
        heading = section["heading"]
        if heading:
            lines.append(heading)
            f5_entries.append(_build_f5(len(heading) + 1, style=_STYLE_HEADING))
        for task in section["tasks"]:
            lines.append(task["text"])
            f5_entries.append(
                _build_f5(
                    len(task["text"]) + 1, style=_STYLE_TODO, done=task["completed"]
                )
            )

    full_text = "\n".join(lines) + "\n"
    text_len = len(full_text)

    f3_entries = [
        _build_f3_run(0, 0, 0, 0, 0, 1),
        _build_f3_run(1, 1, text_len - 1, 1, 0, 2),
        _build_f3_run(1, 0, 1, 1, text_len - 1, 3),
        _build_f3_sentinel(),
    ]

    f4 = _build_f4(replica_uuid, text_len, len(f5_entries) + 1)

    # Assemble String message
    string_msg = field_str(2, full_text)
    for run in f3_entries:
        string_msg += field_bytes(3, run)
    string_msg += field_bytes(4, f4)
    for entry in f5_entries:
        string_msg += field_bytes(5, entry)

    # Wrap: Document(f1=0, f2=Version(f1=0, f2=0, f3=String))
    version_msg = field_bytes(3, string_msg)
    doc_msg = field_varint(1, 0) + field_bytes(
        2, field_varint(1, 0) + field_varint(2, 0) + version_msg
    )

    return gzip.compress(doc_msg)


# --- Database operations ---


def _find_note(db: sqlite3.Connection, folder: str, title: str) -> int | None:
    """Find a note's primary key by folder and title."""
    row = db.execute(
        """
        SELECT n.Z_PK FROM ZICCLOUDSYNCINGOBJECT n
        JOIN ZICCLOUDSYNCINGOBJECT f ON n.ZFOLDER = f.Z_PK
        WHERE f.ZTITLE2 = ? AND n.ZTITLE1 = ?
        AND n.ZMARKEDFORDELETION != 1
        ORDER BY n.ZMODIFICATIONDATE1 DESC LIMIT 1
        """,
        (folder, title),
    ).fetchone()
    return row[0] if row else None


def _quit_notes() -> None:
    """Quit Notes.app so it can't serve or write back its cached copy.

    A running Notes.app keeps notes in memory: it neither picks up our write
    nor guarantees it won't overwrite the row. Quitting first is the only
    reliable order. It re-reads from the database on next launch.
    """
    _osascript(
        'if application "Notes" is running then tell application "Notes" to quit'
    )


def update_note_data(folder: str, title: str, sections: list[dict]) -> bool:
    """Write protobuf with native checklists to Notes database.

    Returns True if updated, False if note not found.
    """
    if not NOTES_DB.exists():
        print(f"  Notes database not found at {NOTES_DB}")
        return False

    _quit_notes()
    print(f"  Writing directly to Notes database at {NOTES_DB}")
    db = sqlite3.connect(str(NOTES_DB))
    try:
        with db:  # auto-commit on success, auto-rollback on exception
            note_pk = _find_note(db, folder, title)
            if not note_pk:
                return False
            protobuf_data = build_note_protobuf(title, sections)
            db.execute(
                "UPDATE ZICNOTEDATA SET ZDATA = ? WHERE ZNOTE = ?",
                (protobuf_data, note_pk),
            )
    except sqlite3.Error as e:
        raise RuntimeError(f"Notes database error: {e}") from None
    finally:
        db.close()

    return True


# --- HTML fallback ---


def create_or_update_note(folder: str, title: str, html_body: str) -> None:
    """Create or update a note via AppleScript (HTML fallback)."""
    esc_title = title.replace('"', '\\"')
    esc_body = html_body.replace("\\", "\\\\").replace('"', '\\"')

    _osascript(f'''
        tell application "Notes"
            if not (exists folder "{folder}") then
                make new folder with properties {{name:"{folder}"}}
            end if
            set targetFolder to folder "{folder}"
            set foundNote to missing value
            repeat with n in (notes of targetFolder)
                if name of n is "{esc_title}" then
                    set foundNote to n
                    exit repeat
                end if
            end repeat
            if foundNote is missing value then
                make new note at targetFolder with properties {{name:"{esc_title}", body:"{esc_body}"}}
            else
                set body of foundNote to "{esc_body}"
            end if
        end tell
    ''')
