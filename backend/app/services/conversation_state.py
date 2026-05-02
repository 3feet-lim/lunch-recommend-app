"""SQLite TTL conversation state for Slack missing-info flow."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

PendingQuestion = Literal["region", "party_size", "context", "none"]


@dataclass(frozen=True, slots=True)
class StateKey:
    team_id: str
    channel_id: str
    user_id: str

    @property
    def value(self) -> str:
        return build_conversation_key(self.team_id, self.channel_id, self.user_id)


@dataclass(frozen=True, slots=True)
class ConversationState:
    pending_question: PendingQuestion
    expires_at: datetime
    key: str = ""
    region: str | None = None
    party_size: int | None = None
    companion_context: str | None = None
    response_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_request_fingerprint: str | None = None

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= _utcnow()


def build_conversation_key(team_id: str, channel_id: str, user_id: str) -> str:
    """Build the PRD-mandated state key: team_id/channel_id/user_id."""

    return f"{team_id}/{channel_id}/{user_id}"


class SQLiteConversationStateStore:
    """Small synchronous SQLite store with last-write-wins semantics."""

    def __init__(
        self,
        db_path: str | Path = "conversation_state.sqlite3",
        *,
        ttl_minutes: int = 30,
    ) -> None:
        self.db_path = str(db_path)
        self.ttl = timedelta(minutes=ttl_minutes)
        self._ensure_schema()

    def get(self, key: str | StateKey) -> ConversationState | None:
        key_value = _key_value(key)
        self.cleanup_expired()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT key, pending_question, region, party_size, companion_context,
                       response_url, created_at, updated_at, expires_at, last_request_fingerprint
                FROM conversation_state WHERE key = ?
                """,
                (key_value,),
            ).fetchone()
        if row is None:
            return None
        state = _state_from_row(row)
        return None if state.is_expired else state

    def upsert(
        self,
        key: str | StateKey,
        state: ConversationState | None = None,
        *,
        pending_question: PendingQuestion = "none",
        region: str | None = None,
        party_size: int | None = None,
        companion_context: str | None = None,
        response_url: str | None = None,
        last_request_fingerprint: str | None = None,
    ) -> ConversationState:
        key_value = _key_value(key)
        if state is not None:
            pending_question = state.pending_question
            region = state.region
            party_size = state.party_size
            companion_context = state.companion_context
            response_url = state.response_url
            last_request_fingerprint = state.last_request_fingerprint
        now = _utcnow()
        existing = self.get(key_value)
        created_at = existing.created_at if existing and existing.created_at else now
        expires_at = state.expires_at if state is not None else now + self.ttl
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_state (
                    key, pending_question, region, party_size, companion_context,
                    response_url, created_at, updated_at, expires_at, last_request_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    pending_question = excluded.pending_question,
                    region = excluded.region,
                    party_size = excluded.party_size,
                    companion_context = excluded.companion_context,
                    response_url = excluded.response_url,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at,
                    last_request_fingerprint = excluded.last_request_fingerprint
                """,
                (
                    key_value,
                    pending_question,
                    region,
                    party_size,
                    companion_context,
                    response_url,
                    _format_dt(created_at),
                    _format_dt(now),
                    _format_dt(expires_at),
                    last_request_fingerprint,
                ),
            )
        persisted = self.get(key_value)
        if persisted is not None:
            return persisted
        return ConversationState(
            key=key_value,
            pending_question=pending_question,
            region=region,
            party_size=party_size,
            companion_context=companion_context,
            response_url=response_url,
            created_at=created_at,
            updated_at=now,
            expires_at=expires_at,
            last_request_fingerprint=last_request_fingerprint,
        )

    def set_fingerprint(self, key: str | StateKey, fingerprint: str) -> ConversationState:
        existing = self.get(key)
        return self.upsert(
            key=key,
            pending_question=existing.pending_question if existing else "none",
            region=existing.region if existing else None,
            party_size=existing.party_size if existing else None,
            companion_context=existing.companion_context if existing else None,
            response_url=existing.response_url if existing else None,
            last_request_fingerprint=fingerprint,
        )

    def is_duplicate(self, key: str | StateKey, fingerprint: str) -> bool:
        existing = self.get(key)
        return existing is not None and existing.last_request_fingerprint == fingerprint

    def delete(self, key: str | StateKey) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM conversation_state WHERE key = ?", (_key_value(key),))

    def cleanup_expired(self) -> int:
        now = _format_dt(_utcnow())
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversation_state WHERE expires_at <= ?", (now,)
            )
            return cursor.rowcount

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_state (
                    key TEXT PRIMARY KEY,
                    pending_question TEXT NOT NULL,
                    region TEXT,
                    party_size INTEGER,
                    companion_context TEXT,
                    response_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_request_fingerprint TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


# Short alias for callers/tests that prefer a generic name.
ConversationStateStore = SQLiteConversationStateStore


def _state_from_row(row: sqlite3.Row) -> ConversationState:
    return ConversationState(
        key=str(row["key"]),
        pending_question=_pending_question(str(row["pending_question"])),
        region=row["region"],
        party_size=row["party_size"],
        companion_context=row["companion_context"],
        response_url=row["response_url"],
        created_at=_parse_dt(str(row["created_at"])),
        updated_at=_parse_dt(str(row["updated_at"])),
        expires_at=_parse_dt(str(row["expires_at"])),
        last_request_fingerprint=row["last_request_fingerprint"],
    )


def _key_value(key: str | StateKey) -> str:
    return key.value if isinstance(key, StateKey) else key


def _pending_question(value: str) -> PendingQuestion:
    if value in {"region", "party_size", "context", "none"}:
        return value  # type: ignore[return-value]
    return "none"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _format_dt(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
