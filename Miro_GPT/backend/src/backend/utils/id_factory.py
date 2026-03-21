from __future__ import annotations

import uuid


def prefixed_id(prefix: str, size: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:size]}"
