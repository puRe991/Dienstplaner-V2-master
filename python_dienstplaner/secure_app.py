from __future__ import annotations

from pathlib import Path
from typing import Any
import tkinter as tk
from tkinter import messagebox

from .app import SchedulerApp
from .application_service import SchedulerApplicationService
from .auth import Permission, User, UserRole
from .auth_ui import authenticate_on_start, user_label, user_has_permission
from .repository import SQLiteSchedulerRepository


class AuthenticatedSchedulerApp(SchedulerApp):
    """Scheduler shell with local login and role-based action guards.

    The subclass keeps authentication wiring out of app.py. This avoids merge
    conflicts in the main scheduler shell while preserving a secured startup path
    for the default launcher.
    """

    def __init__(self, service, repository: SQLiteSchedulerRepository, current_user: User | None = None) -> None:
        self.current_user: User | None = current_user
        self.application_service = SchedulerApplicationService(service, current_user)
        super().__init__(service, repository)

    def _configure_styles(self) -> None:
        super()._configure_styles()
        if self.current_user is None:
            self.current_user = authenticate_on_start(self, self.repository)
            self.application_service.set_current_user(self.current_user)

    def _build_header(self) -> None:
        super()._build_header()
        header = self.notification_label.master
        tk.Label(
            header,
            text=user_label(self.current_user),
            bg="#FFFFFF",
            fg="#0F172A",
            justify="left",
            font=("Segoe UI", 10),
        ).grid(row=0, column=4, padx=(0, 24))

    @staticmethod
    def _user_has_permission(user: User | None, permission: Permission) -> bool:
        return user_has_permission(user, permission)

    def _require_permission(self, permission: Permission, action: str, parent: tk.Misc | None = None) -> bool:
        if self.application_service.has_permission(permission):
            return True
        messagebox.showwarning("Keine Berechtigung", f"Sie haben keine Berechtigung für: {action}", parent=parent or self)
        self._set_status(f"Aktion gesperrt: {action}")
        return False

    def _current_user_id(self) -> str:
        return self.application_service.audit_context.user_id


    def _add_employee(self, *args: Any, **kwargs: Any):
        kwargs.pop("user_id", None)
        return self.application_service.add_employee(*args, **kwargs)

    def _update_employee(self, *args: Any, **kwargs: Any):
        kwargs.pop("user_id", None)
        return self.application_service.update_employee(*args, **kwargs)

    def _delete_employee(self, employee_id: str) -> bool:
        return self.application_service.delete_employee(employee_id)

    def _add_absence(self, *args: Any, **kwargs: Any):
        kwargs.pop("user_id", None)
        return self.application_service.add_absence(*args, **kwargs)

    def _delete_absence_record(self, absence_id: str) -> bool:
        return self.application_service.delete_absence(absence_id)

    def _publish_week(self) -> int:
        return self.application_service.publish_week(self.week_start)

    def _export_schedule(self, path, export_format):
        return self.application_service.export_schedule(path, export_format)

    def _export_reports(self, path):
        return self.application_service.export_reports(path)

    def _set_active_rule_profile(self, profile_id: str):
        return self.application_service.set_active_rule_profile(profile_id)

    def _add_rule_profile(self, profile):
        return self.application_service.add_rule_profile(profile)

    def _update_rule_profile(self, profile_id: str, updated):
        return self.application_service.update_rule_profile(profile_id, updated)

    def _delete_rule_profile(self, profile_id: str) -> bool:
        return self.application_service.delete_rule_profile(profile_id)

    def _open_employee_manager(self) -> None:
        if self._require_permission(Permission.MANAGE_EMPLOYEES, "Mitarbeiter bearbeiten"):
            super()._open_employee_manager()

    def _open_employee_dialog(self, employee=None):
        if not self._require_permission(Permission.MANAGE_EMPLOYEES, "Mitarbeiter bearbeiten"):
            return None
        return super()._open_employee_dialog(employee)

    def _open_absence_manager(self) -> None:
        if self._require_permission(Permission.MANAGE_ABSENCES, "Abwesenheiten bearbeiten"):
            super()._open_absence_manager()

    def _open_settings_window(self) -> None:
        if self._require_permission(Permission.MANAGE_RULE_PROFILES, "Regelprofile verwalten"):
            super()._open_settings_window()

    def _open_absence_dialog(self):
        if not self._require_permission(Permission.MANAGE_ABSENCES, "Abwesenheiten bearbeiten"):
            return None
        return super()._open_absence_dialog()

    def _delete_absence(self, absence_id: str) -> None:
        if self._require_permission(Permission.MANAGE_ABSENCES, "Abwesenheiten löschen"):
            super()._delete_absence(absence_id)

    def _open_audit_log_window(self) -> None:
        if self.current_user is not None and self.current_user.role == UserRole.ADMIN:
            super()._open_audit_log_window()
            return
        messagebox.showwarning("Keine Berechtigung", "Sie haben keine Berechtigung für: Änderungsverlauf anzeigen", parent=self)
        self._set_status("Aktion gesperrt: Änderungsverlauf anzeigen")

    def _export_reports_csv(self) -> None:
        if self._require_permission(Permission.EXPORT, "Export"):
            super()._export_reports_csv()

    def _export_csv(self) -> None:
        if self._require_permission(Permission.EXPORT, "Export"):
            super()._export_csv()

    def _publish_schedule(self) -> None:
        if not self._require_permission(Permission.PUBLISH_SCHEDULE, "Dienstplan veröffentlichen"):
            return
        try:
            count = self._publish_week()
            if not self._persist_changes(f"Dienstplan veröffentlicht: {count} Schichten gespeichert."):
                return
            self._refresh_all()
        except ValueError as exc:
            messagebox.showwarning("Dienstplan prüfen", str(exc), parent=self)
        except OSError as exc:
            messagebox.showerror("Veröffentlichung fehlgeschlagen", str(exc), parent=self)


def create_app(database_path: str | Path = "python_dienstplaner/data/dienstplaner.sqlite3") -> AuthenticatedSchedulerApp:
    repository = SQLiteSchedulerRepository(database_path)
    service = repository.load()
    return AuthenticatedSchedulerApp(service, repository)


def main() -> None:
    app = create_app()
    app.mainloop()
