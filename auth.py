"""
V.A.U.L.T. - Authentication / Session Layer
"""

import secrets
import threading
from datetime import datetime, timezone


# Active browser sessions.
# token -> authenticated user
SESSIONS = {}

SESSIONS_LOCK = threading.Lock()


def create_session(user):
    """
    Create a secure session token for an authenticated user.
    """

    token = secrets.token_urlsafe(32)

    session_data = {
        "user_id": user["id"],
        "operator_id": user["operator_id"],
        "name": user["name"],
        "role": user["role"],
        "organization": user["organization"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with SESSIONS_LOCK:
        SESSIONS[token] = session_data

    return token


def get_session(token):
    """
    Return session information for a valid token.
    """

    if not token:
        return None

    with SESSIONS_LOCK:
        session = SESSIONS.get(token)

    return dict(session) if session else None


def destroy_session(token):
    """
    Remove an active session.
    """

    if not token:
        return

    with SESSIONS_LOCK:
        SESSIONS.pop(token, None)


def is_authenticated(token):
    """
    Check whether a session token represents an authenticated user.
    """

    return get_session(token) is not None