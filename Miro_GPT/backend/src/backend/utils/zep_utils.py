from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from zep_cloud import InternalServerError
from zep_cloud.client import Zep


def _fetch_page_with_retry(
    api_call: Callable[..., list[Any]],
    *args: Any,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    **kwargs: Any,
) -> list[Any]:
    last_exception: Exception | None = None
    delay = retry_delay
    for attempt in range(max_retries):
        try:
            return api_call(*args, **kwargs)
        except (ConnectionError, TimeoutError, OSError, InternalServerError) as error:
            last_exception = error
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
    if last_exception is None:
        raise RuntimeError("Unknown Zep paging failure")
    raise last_exception


def fetch_all_nodes(client: Zep, graph_id: str, page_size: int = 100) -> list[Any]:
    nodes: list[Any] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {"limit": page_size}
        if cursor:
            kwargs["uuid_cursor"] = cursor
        batch = _fetch_page_with_retry(client.graph.node.get_by_graph_id, graph_id, **kwargs)
        if not batch:
            break
        nodes.extend(batch)
        if len(batch) < page_size:
            break
        cursor = getattr(batch[-1], "uuid_", None) or getattr(batch[-1], "uuid", None)
        if cursor is None:
            break
    return nodes


def fetch_all_edges(client: Zep, graph_id: str, page_size: int = 100) -> list[Any]:
    edges: list[Any] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {"limit": page_size}
        if cursor:
            kwargs["uuid_cursor"] = cursor
        batch = _fetch_page_with_retry(client.graph.edge.get_by_graph_id, graph_id, **kwargs)
        if not batch:
            break
        edges.extend(batch)
        if len(batch) < page_size:
            break
        cursor = getattr(batch[-1], "uuid_", None) or getattr(batch[-1], "uuid", None)
        if cursor is None:
            break
    return edges
