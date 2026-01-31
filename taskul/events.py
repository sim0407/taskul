"""Event recording (append-only audit log). Used by commands and API."""
import json


def record_event(
    conn,
    actor: str,
    event_type: str,
    payload: dict | str | None = None,
) -> None:
    """
    Append an event to the events table. Caller must commit.
    actor: "human" | "agent"
    event_type: e.g. TASK_CREATED, TASK_UPDATED, TASK_MOVED, DEP_CREATED, DEP_REMOVED
    payload: dict (will be json.dumps) or str, or None
    """
    if actor not in ("human", "agent"):
        raise ValueError("actor must be 'human' or 'agent'")
    payload_str = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else (payload or "")
    conn.execute(
        "INSERT INTO events (actor, type, payload) VALUES (?, ?, ?)",
        (actor, event_type, payload_str),
    )
