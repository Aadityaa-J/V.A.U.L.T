"""
V.A.U.L.T. - Database Layer
SQLite-backed authentication, private User Library, and shared Global KB.

Storage ownership:
    uploaded_files/  -> private user uploads
    knowledge_files/ -> shared Global Knowledge Base

The database stores metadata only; file bytes remain on the local filesystem.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "vault.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _table_columns(connection, table_name):
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def _migrate_library_schema(connection):
    """Migrate older Library schemas to (user_id, original_name) uniqueness."""
    columns = _table_columns(connection, "library_files")
    if not columns:
        return

    required = {
        "id", "user_id", "original_name", "stored_name", "storage_path",
        "mime_type", "file_extension", "file_size", "content_hash",
        "uploaded_at", "processing_status", "ocr_used", "chunk_count",
    }
    if not required.issubset(columns):
        connection.execute("DROP TABLE IF EXISTS library_files")
        columns = []

    # The original implementation used UNIQUE(user_id, content_hash), but the
    # application contract is filename-based replacement within each user's
    # Library. Rebuild only when that old constraint is still present.
    sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='library_files'"
    ).fetchone()
    table_sql = (sql[0] or "").lower() if sql else ""
    if columns and "unique (user_id, original_name)" not in table_sql:
        connection.execute("ALTER TABLE library_files RENAME TO library_files_old")
        connection.execute(
            """
            CREATE TABLE library_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                mime_type TEXT DEFAULT '',
                file_extension TEXT DEFAULT '',
                file_size INTEGER NOT NULL DEFAULT 0,
                content_hash TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                processing_status TEXT NOT NULL DEFAULT 'stored',
                ocr_used INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, original_name)
            )
            """
        )
        old_columns = set(_table_columns(connection, "library_files_old"))
        copy_columns = [
            name for name in required
            if name in old_columns and name != "id"
        ]
        # Preserve IDs when possible; it makes existing references/debugging
        # easier and is safe because the table is freshly created.
        if "id" in old_columns:
            cols = ["id"] + copy_columns
            connection.execute(
                f"INSERT OR IGNORE INTO library_files ({', '.join(cols)}) "
                f"SELECT {', '.join(cols)} FROM library_files_old"
            )
        else:
            connection.execute(
                f"INSERT OR IGNORE INTO library_files ({', '.join(copy_columns)}) "
                f"SELECT {', '.join(copy_columns)} FROM library_files_old"
            )
        connection.execute("DROP TABLE library_files_old")


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'User',
                organization TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS library_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                mime_type TEXT DEFAULT '',
                file_extension TEXT DEFAULT '',
                file_size INTEGER NOT NULL DEFAULT 0,
                content_hash TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                processing_status TEXT NOT NULL DEFAULT 'stored',
                ocr_used INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, original_name)
            )
            """
        )
        _migrate_library_schema(connection)

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_base_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT UNIQUE NOT NULL,
                stored_name TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                mime_type TEXT DEFAULT '',
                file_extension TEXT DEFAULT '',
                file_size INTEGER NOT NULL DEFAULT 0,
                content_hash TEXT NOT NULL,
                added_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                processing_status TEXT NOT NULL DEFAULT 'pending',
                ocr_used INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                summary TEXT DEFAULT '',
                preview TEXT DEFAULT ''
            )
            """
        )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_library_files_user_id "
            "ON library_files(user_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_library_files_user_name "
            "ON library_files(user_id, original_name)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_files_name "
            "ON knowledge_base_files(original_name)"
        )
        connection.commit()


def hash_password(password: str, salt: str | None = None):
    if salt is None:
        salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()
    return password_hash, salt


def verify_password(password: str, stored_hash: str, salt: str):
    password_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(password_hash, stored_hash)


def create_user(operator_id, password, name, role="User", organization=""):
    password_hash, password_salt = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users
                (operator_id, password_hash, password_salt, name, role, organization, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (operator_id, password_hash, password_salt, name, role, organization, created_at),
            )
            connection.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def authenticate_user(operator_id, password):
    with get_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE operator_id = ? AND is_active = 1",
            (operator_id,),
        ).fetchone()
    if user is None:
        return None
    if not verify_password(password, user["password_hash"], user["password_salt"]):
        return None
    return dict(user)


def get_user_by_operator_id(operator_id):
    with get_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE operator_id = ?", (operator_id,)
        ).fetchone()
    return dict(user) if user else None


# ---------------------------------------------------------------------------
# PRIVATE USER LIBRARY
# ---------------------------------------------------------------------------

def add_library_file(user_id, original_name, stored_name, storage_path,
                     mime_type, file_extension, file_size, content_hash):
    uploaded_at = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO library_files
                (user_id, original_name, stored_name, storage_path, mime_type,
                 file_extension, file_size, content_hash, uploaded_at,
                 processing_status, ocr_used, chunk_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'stored', 0, 0)
                """,
                (user_id, original_name, stored_name, storage_path, mime_type,
                 file_extension, file_size, content_hash, uploaded_at),
            )
            connection.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_library_file_by_hash(user_id, content_hash):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM library_files WHERE user_id = ? AND content_hash = ?",
            (user_id, content_hash),
        ).fetchone()
    return dict(row) if row else None


def get_library_file_by_name(user_id, original_name):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM library_files WHERE user_id = ? AND original_name = ? LIMIT 1",
            (user_id, original_name),
        ).fetchone()
    return dict(row) if row else None


def get_library_files(user_id):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, original_name, stored_name, storage_path, mime_type,
                   file_extension, file_size, content_hash, uploaded_at,
                   processing_status, ocr_used, chunk_count
            FROM library_files
            WHERE user_id = ?
            ORDER BY uploaded_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_library_file(file_id, user_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM library_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def update_library_file(file_id, user_id, **fields):
    allowed = {
        "original_name", "stored_name", "storage_path", "mime_type",
        "file_extension", "file_size", "content_hash", "processing_status",
        "ocr_used", "chunk_count",
    }
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return False
    assignments = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [file_id, user_id]
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE library_files SET {assignments} WHERE id = ? AND user_id = ?",
            values,
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_library_file(file_id, user_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT storage_path FROM library_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            "DELETE FROM library_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        )
        connection.commit()
    return row["storage_path"]


# ---------------------------------------------------------------------------
# SHARED GLOBAL KNOWLEDGE BASE
# ---------------------------------------------------------------------------

def add_knowledge_file(original_name, stored_name, storage_path, mime_type,
                       file_extension, file_size, content_hash, summary="", preview=""):
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO knowledge_base_files
                (original_name, stored_name, storage_path, mime_type,
                 file_extension, file_size, content_hash, added_at, updated_at,
                 processing_status, ocr_used, chunk_count, summary, preview)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, 0, ?, ?)
                """,
                (original_name, stored_name, storage_path, mime_type,
                 file_extension, file_size, content_hash, now, now, summary, preview),
            )
            connection.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_knowledge_files():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM knowledge_base_files
            ORDER BY added_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_knowledge_file(file_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM knowledge_base_files WHERE id = ?",
            (file_id,),
        ).fetchone()
    return dict(row) if row else None


def get_knowledge_file_by_name(original_name):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM knowledge_base_files WHERE original_name = ? LIMIT 1",
            (original_name,),
        ).fetchone()
    return dict(row) if row else None


def get_knowledge_file_by_hash(content_hash):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM knowledge_base_files WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        ).fetchone()
    return dict(row) if row else None


def update_knowledge_file(file_id, **fields):
    allowed = {
        "original_name", "stored_name", "storage_path", "mime_type",
        "file_extension", "file_size", "content_hash", "processing_status",
        "ocr_used", "chunk_count", "summary", "preview",
    }
    fields = {k: v for k, v in fields.items() if k in allowed}
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    assignments = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [file_id]
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE knowledge_base_files SET {assignments} WHERE id = ?",
            values,
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_knowledge_file(file_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT storage_path FROM knowledge_base_files WHERE id = ?",
            (file_id,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            "DELETE FROM knowledge_base_files WHERE id = ?",
            (file_id,),
        )
        connection.commit()
    return row["storage_path"]


initialize_database()
