from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class UserRole(str, Enum):
    ADMIN = "admin"
    PLANNER = "planner"
    VIEWER = "viewer"


class Permission(str, Enum):
    EXPORT = "export"
    PUBLISH_SCHEDULE = "publish_schedule"
    MANAGE_ABSENCES = "manage_absences"
    MANAGE_EMPLOYEES = "manage_employees"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.PLANNER: frozenset({Permission.EXPORT, Permission.PUBLISH_SCHEDULE, Permission.MANAGE_ABSENCES}),
    UserRole.VIEWER: frozenset(),
}


@dataclass(frozen=True)
class User:
    username: str
    role: UserRole
    id: str = field(default_factory=lambda: str(uuid4()))
    display_name: str = ""
    password_hash: str = ""
    password_salt: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        username = self.username.strip()
        display_name = self.display_name.strip()
        if not username:
            raise ValueError("Benutzername ist erforderlich.")
        object.__setattr__(self, "username", username)
        object.__setattr__(self, "display_name", display_name or username)
        if not isinstance(self.role, UserRole):
            object.__setattr__(self, "role", UserRole(str(self.role)))

    def has_permission(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]
