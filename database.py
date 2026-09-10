"""
V.A.U.L.T. - Database Layer
SQLite-backed users and user-specific Library metadata.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import secrets

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "vault.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


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

        # The original schema used (user_id, content_hash) as the UNIQUE key.
        # V.A.U.L.T. now intentionally de-duplicates by filename instead:
        # the same user can have one current Library entry for a given name,
        # while identical content under different names remains separate.
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='library_files'"
        ).fetchone()

        if table_exists:
            unique_indexes = connection.execute(
                "PRAGMA index_list(library_files)"
            ).fetchall()
            filename_unique = False
            for index in unique_indexes:
                if not index[2]:
                    continue
                index_name = index[1]
                columns = connection.execute(
                    f'PRAGMA index_info("{index_name}")'
                ).fetchall()
                column_names = [row[2] for row in columns]
                if column_names == ["user_id", "original_name"]:
                    filename_unique = True
                    break

            if not filename_unique:
                connection.execute("ALTER TABLE library_files RENAME TO library_files_legacy")
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
                # Keep the newest record when a legacy database somehow already
                # contains the same filename more than once.
                connection.execute(
                    """
                    INSERT INTO library_files (
                        id, user_id, original_name, stored_name, storage_path,
                        mime_type, file_extension, file_size, content_hash,
                        uploaded_at, processing_status, ocr_used, chunk_count
                    )
                    SELECT id, user_id, original_name, stored_name, storage_path,
                           mime_type, file_extension, file_size, content_hash,
                           uploaded_at, processing_status, ocr_used, chunk_count
                    FROM library_files_legacy AS old
                    WHERE old.id = (
                        SELECT newer.id
                        FROM library_files_legacy AS newer
                        WHERE newer.user_id = old.user_id
                          AND newer.original_name = old.original_name
                        ORDER BY newer.uploaded_at DESC, newer.id DESC
                        LIMIT 1
                    )
                    """
                )
                connection.execute("DROP TABLE library_files_legacy")
        else:
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

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_library_files_user_id "
            "ON library_files(user_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_library_files_user_name "
            "ON library_files(user_id, original_name)"
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


def create_user(
    operator_id: str,
    password: str,
    name: str,
    role: str = "User",
    organization: str = "",
):
    password_hash, password_salt = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    operator_id,
                    password_hash,
                    password_salt,
                    name,
                    role,
                    organization,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operator_id,
                    password_hash,
                    password_salt,
                    name,
                    role,
                    organization,
                    created_at,
                ),
            )
            connection.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def authenticate_user(operator_id: str, password: str):
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE operator_id = ?
              AND is_active = 1
            """,
            (operator_id,),
        ).fetchone()

    if user is None:
        return None

    if not verify_password(
        password,
        user["password_hash"],
        user["password_salt"],
    ):
        return None

    return dict(user)


def get_user_by_operator_id(operator_id: str):
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE operator_id = ?
            """,
            (operator_id,),
        ).fetchone()

    return dict(user) if user else None


def add_library_file(
    user_id: int,
    original_name: str,
    stored_name: str,
    storage_path: str,
    mime_type: str,
    file_extension: str,
    file_size: int,
    content_hash: str,
):
    uploaded_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO library_files (
                    user_id,
                    original_name,
                    stored_name,
                    storage_path,
                    mime_type,
                    file_extension,
                    file_size,
                    content_hash,
                    uploaded_at,
                    processing_status,
                    ocr_used,
                    chunk_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'stored', 0, 0)
                """,
                (
                    user_id,
                    original_name,
                    stored_name,
                    storage_path,
                    mime_type,
                    file_extension,
                    file_size,
                    content_hash,
                    uploaded_at,
                ),
            )
            connection.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_library_file_by_hash(user_id: int, content_hash: str):
    """Return the user's existing Library record for an exact content hash."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM library_files
            WHERE user_id = ? AND content_hash = ?
            """,
            (user_id, content_hash),
        ).fetchone()

    return dict(row) if row else None



def get_library_file_by_name(user_id: int, original_name: str):
    """Return the authenticated user's Library record for a filename."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM library_files
            WHERE user_id = ? AND original_name = ?
            """,
            (user_id, original_name),
        ).fetchone()
    return dict(row) if row else None


def update_library_file(
    file_id: int,
    user_id: int,
    original_name: str,
    stored_name: str,
    storage_path: str,
    mime_type: str,
    file_extension: str,
    file_size: int,
    content_hash: str,
):
    """Update a user's existing filename entry after its content changes."""
    uploaded_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE library_files
            SET original_name = ?,
                stored_name = ?,
                storage_path = ?,
                mime_type = ?,
                file_extension = ?,
                file_size = ?,
                content_hash = ?,
                uploaded_at = ?,
                processing_status = 'stored',
                ocr_used = 0,
                chunk_count = 0
            WHERE id = ? AND user_id = ?
            """,
            (
                original_name,
                stored_name,
                storage_path,
                mime_type,
                file_extension,
                file_size,
                content_hash,
                uploaded_at,
                file_id,
                user_id,
            ),
        )
        connection.commit()
        return cursor.rowcount > 0


def get_library_files(user_id: int):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                original_name,
                stored_name,
                mime_type,
                file_extension,
                file_size,
                content_hash,
                uploaded_at,
                processing_status,
                ocr_used,
                chunk_count
            FROM library_files
            WHERE user_id = ?
            ORDER BY uploaded_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_library_file(file_id: int, user_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM library_files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user_id),
        ).fetchone()

    return dict(row) if row else None


def delete_library_file(file_id: int, user_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT storage_path
            FROM library_files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user_id),
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            """
            DELETE FROM library_files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user_id),
        )
        connection.commit()

    return row["storage_path"]


initialize_database()
