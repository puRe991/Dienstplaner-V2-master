from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .auth import Permission, User
from .exporters import ExportHeader, ExportOptions
from .models import Absence, Employee, ExportFormat, RuleProfile
from .services import SchedulerService


class AuthorizationError(PermissionError, ValueError):
    """Raised when the current user may not execute an application action."""


@dataclass(frozen=True)
class AuditContext:
    user_id: str
    display_name: str


class SchedulerApplicationService:
    """Authorization boundary for productive scheduler mutations.

    UI code may still disable buttons and show feedback, but this service owns the
    final decision before state-changing operations reach ``SchedulerService``.
    """

    def __init__(self, scheduler: SchedulerService, current_user: User | None = None) -> None:
        self.scheduler = scheduler
        self.current_user = current_user

    @property
    def audit_context(self) -> AuditContext:
        if self.current_user is None:
            return AuditContext(user_id="local", display_name="Lokaler Benutzer")
        return AuditContext(user_id=self.current_user.id, display_name=self.current_user.display_name)

    def set_current_user(self, user: User | None) -> None:
        self.current_user = user

    def has_permission(self, permission: Permission) -> bool:
        return self.current_user is not None and self.current_user.is_active and self.current_user.has_permission(permission)

    def require_permission(self, permission: Permission) -> None:
        if not self.has_permission(permission):
            raise AuthorizationError(f"Keine Berechtigung für: {permission.value}")

    def add_employee(self, *args: Any, **kwargs: Any) -> Employee:
        self.require_permission(Permission.MANAGE_EMPLOYEES)
        return self.scheduler.add_employee(*args, user_id=self.audit_context.user_id, **kwargs)

    def update_employee(self, *args: Any, **kwargs: Any) -> Employee:
        self.require_permission(Permission.MANAGE_EMPLOYEES)
        return self.scheduler.update_employee(*args, user_id=self.audit_context.user_id, **kwargs)

    def delete_employee(self, employee_id: str) -> bool:
        self.require_permission(Permission.MANAGE_EMPLOYEES)
        return self.scheduler.delete_employee(employee_id, user_id=self.audit_context.user_id)

    def add_absence(self, employee_id: str, start: datetime, end: datetime, reason: str = "") -> Absence:
        self.require_permission(Permission.MANAGE_ABSENCES)
        return self.scheduler.add_absence(employee_id, start, end, reason, user_id=self.audit_context.user_id)

    def delete_absence(self, absence_id: str) -> bool:
        self.require_permission(Permission.MANAGE_ABSENCES)
        return self.scheduler.delete_absence(absence_id, user_id=self.audit_context.user_id)

    def publish_week(self, week_start: datetime) -> int:
        self.require_permission(Permission.PUBLISH_SCHEDULE)
        return self.scheduler.publish_week(week_start, self.audit_context.display_name, user_id=self.audit_context.user_id)

    def export_schedule(
        self,
        path: str | Path,
        export_format: ExportFormat = ExportFormat.CSV,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        self.require_permission(Permission.EXPORT)
        return self.scheduler.export_schedule(path, export_format, options=options, header=header, user_id=self.audit_context.user_id)

    def export_reports(self, path: str | Path) -> Path:
        self.require_permission(Permission.EXPORT)
        return self.scheduler.export_reports(path, user_id=self.audit_context.user_id)

    def set_active_rule_profile(self, profile_id: str) -> RuleProfile:
        self.require_permission(Permission.MANAGE_RULE_PROFILES)
        return self.scheduler.set_active_rule_profile(profile_id)

    def add_rule_profile(self, profile: RuleProfile) -> RuleProfile:
        self.require_permission(Permission.MANAGE_RULE_PROFILES)
        return self.scheduler.add_rule_profile(profile)

    def update_rule_profile(self, profile_id: str, updated: RuleProfile) -> RuleProfile:
        self.require_permission(Permission.MANAGE_RULE_PROFILES)
        return self.scheduler.update_rule_profile(profile_id, updated)

    def delete_rule_profile(self, profile_id: str) -> bool:
        self.require_permission(Permission.MANAGE_RULE_PROFILES)
        return self.scheduler.delete_rule_profile(profile_id)
