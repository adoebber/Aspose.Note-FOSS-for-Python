from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LogicalNode:
    kind: str
    oid: Any
    properties: dict[str, Any] = field(default_factory=dict)
    children: list[LogicalNode] = field(default_factory=list)
    metadata: list[LogicalNode] = field(default_factory=list)


@dataclass(slots=True)
class LogicalDocument:
    root: LogicalNode | None
