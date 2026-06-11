from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit entry storing actor, action, target and JSON snapshots."""

    timestamp: datetime
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    before: str = ""
    after: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        action = str(self.action).strip()
        entity_type = str(self.entity_type).strip()
        if not action:
            raise ValueError("Audit-Aktion ist erforderlich.")
        if not entity_type:
            raise ValueError("Audit-Entitätstyp ist erforderlich.")
        object.__setattr__(self, "user_id", str(self.user_id or "system").strip() or "system")
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "entity_type", entity_type)
        object.__setattr__(self, "entity_id", str(self.entity_id or "").strip())
        object.__setattr__(self, "before", str(self.before or ""))
        object.__setattr__(self, "after", str(self.after or ""))
