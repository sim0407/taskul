"""Dependency cycle detection and parent-chain cycle detection."""
from __future__ import annotations

import sqlite3

from .db import get_all_dependencies, get_task_parent_chain


def would_create_cycle(
    conn: sqlite3.Connection,
    from_task_id: str,
    to_task_id: str,
) -> bool:
    """
    Returns True if adding edge from_task_id -> to_task_id would create a cycle
    in the dependency graph. Assumes from_task_id != to_task_id.
    """
    if from_task_id == to_task_id:
        return True
    edges = get_all_dependencies(conn)
    # Build adjacency: from -> [to, ...]
    adj: dict[str, list[str]] = {}
    for f, t in edges:
        adj.setdefault(f, []).append(t)
    # Add the candidate edge
    adj.setdefault(from_task_id, []).append(to_task_id)

    # DFS from to_task_id: if we can reach from_task_id, we have a cycle
    visited = set()

    def reachable(node: str, target: str) -> bool:
        if node == target:
            return True
        if node in visited:
            return False
        visited.add(node)
        for neighbor in adj.get(node, []):
            if reachable(neighbor, target):
                return True
        return False

    return reachable(to_task_id, from_task_id)


def would_create_parent_cycle(
    conn: sqlite3.Connection,
    task_id: str,
    new_parent_id: str,
) -> bool:
    """
    Returns True if setting task_id's parent_task_id to new_parent_id would create a cycle
    (task would become its own ancestor). Also returns True if task_id == new_parent_id.
    """
    if task_id == new_parent_id:
        return True
    if not new_parent_id:
        return False
    ancestors = get_task_parent_chain(conn, task_id)
    return new_parent_id in ancestors
