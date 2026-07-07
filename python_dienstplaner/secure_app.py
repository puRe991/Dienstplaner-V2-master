from __future__ import annotations

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .app import SchedulerApp
from .auth import Permission, User, UserRole
from .auth_ui import authenticate_on_start, user_label, user_has_permission
from .licensing import LicenseCheckResult, LicenseManager
from .repository import SQLiteSchedulerRepository


ROLE_LABELS: dict[UserRole, str] = {
    UserRole.ADMIN: "Administrator",
    UserRole.PLANNER: "Planer",
    UserRole.VIEWER: "Betrachter",
}
ROLE_BY_LABEL: dict[str, UserRole] = {label: role for role, label in ROLE_LABELS.items()}


def default_database_path() -> Path:
    configured_path = os.environ.get("DIENSTPLANER_DATABASE_PATH")
    if configured_path:
        return Path(configured_path).expanduser()
    if getattr(sys, "frozen", False):
        app_data = os.environ.get("APPDATA") or str(Path.home())
        return Path(app_data) / "Dienstplaner" / "data" / "dienstplaner.sqlite3"
    return Path("python_dienstplaner/data/dienstplaner.sqlite3")


class AuthenticatedSchedulerApp(SchedulerApp):
    """Scheduler shell with local login and role-based action guards.

    The subclass keeps authentication wiring out of app.py. This avoids merge
    conflicts in the main scheduler shell while preserving a secured startup path
    for the default launcher.
    """

    def __init__(
        self,
        service,
        repository: SQLiteSchedulerRepository,
        current_user: User | None = None,
        license_result: LicenseCheckResult | None = None,
    ) -> None:
        self.current_user: User | None = current_user
        super().__init__(service, repository, license_result)

    def _configure_styles(self) -> None:
        super()._configure_styles()
        if self.current_user is None:
            self.current_user = authenticate_on_start(self, self.repository)

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
        ).grid(row=0, column=5, padx=(0, 24))
        if self.current_user is not None and self.current_user.role == UserRole.ADMIN:
            ttk.Button(
                header,
                text="🔑 Benutzer verwalten",
                style="Ghost.TButton",
                command=self._open_user_manager,
            ).grid(row=0, column=6, padx=(0, 20))

    @staticmethod
    def _user_has_permission(user: User | None, permission: Permission) -> bool:
        return user_has_permission(user, permission)

    def _require_permission(self, permission: Permission, action: str, parent: tk.Misc | None = None) -> bool:
        if self._user_has_permission(self.current_user, permission):
            return True
        messagebox.showwarning("Keine Berechtigung", f"Sie haben keine Berechtigung für: {action}", parent=parent or self)
        self._set_status(f"Aktion gesperrt: {action}")
        return False

    def _current_user_id(self) -> str:
        return self.current_user.id if self.current_user else "local"

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
            published_by = self.current_user.display_name if self.current_user else "Lokaler Benutzer"
            count = self.service.publish_week(self.week_start, published_by, user_id=self._current_user_id())
            if not self._persist_changes(f"Dienstplan veröffentlicht: {count} Schichten gespeichert."):
                return
            self._refresh_all()
        except ValueError as exc:
            messagebox.showwarning("Dienstplan prüfen", str(exc), parent=self)
        except OSError as exc:
            messagebox.showerror("Veröffentlichung fehlgeschlagen", str(exc), parent=self)

    def _open_user_manager(self) -> None:
        if not self._require_permission(Permission.MANAGE_USERS, "Benutzer verwalten"):
            return
        window = self._create_manager_window("Benutzer verwalten", "860x480")
        columns = ("username", "display_name", "role", "status")
        tree = self._create_tree(window, columns, {
            "username": "Benutzername",
            "display_name": "Anzeigename",
            "role": "Rolle",
            "status": "Status",
        })

        def refresh() -> None:
            self._clear_tree(tree)
            for user in self.repository.list_users():
                tree.insert("", "end", iid=user.id, values=(
                    user.username,
                    user.display_name,
                    ROLE_LABELS.get(user.role, user.role.value),
                    "Aktiv" if user.is_active else "Inaktiv",
                ))

        def selected_user() -> User | None:
            selection = tree.selection()
            return self.repository.get_user(selection[0]) if selection else None

        def add_user() -> None:
            dialog = self._open_create_user_dialog(window, on_saved=refresh)
            window.wait_window(dialog)

        def change_role() -> None:
            user = selected_user()
            if user is None:
                self._set_status("Bitte einen Benutzer auswählen.")
                return
            dialog = self._open_role_dialog(window, user, on_saved=refresh)
            window.wait_window(dialog)

        def toggle_active() -> None:
            user = selected_user()
            if user is None:
                self._set_status("Bitte einen Benutzer auswählen.")
                return
            action_label = "Benutzer deaktivieren" if user.is_active else "Benutzer aktivieren"
            confirm_text = (
                f"Soll {user.display_name} wirklich deaktiviert werden?"
                if user.is_active
                else f"Soll {user.display_name} wieder aktiviert werden?"
            )
            if not messagebox.askyesno(action_label, confirm_text, parent=window):
                return
            try:
                if not user.is_active:
                    self._check_active_user_limit()
                self.repository.set_user_active(user.id, not user.is_active, user_id=self._current_user_id())
                self._set_status(f"{action_label}: {user.display_name}.")
                refresh()
            except ValueError as exc:
                messagebox.showerror(action_label, str(exc), parent=window)

        def reset_password() -> None:
            user = selected_user()
            if user is None:
                self._set_status("Bitte einen Benutzer auswählen.")
                return
            dialog = self._open_password_reset_dialog(window, user)
            window.wait_window(dialog)

        self._add_manager_buttons(window, [
            ("Neu", add_user),
            ("Rolle ändern", change_role),
            ("Aktivieren/Deaktivieren", toggle_active),
            ("Passwort zurücksetzen", reset_password),
            ("Aktualisieren", refresh),
        ])
        tree.bind("<Double-Button-1>", lambda _event: change_role())
        refresh()

    def _license_seat_hint(self) -> str | None:
        license_info = self.license_result.license_info
        if license_info is None:
            return None
        active = self.repository.active_user_count()
        return (
            f"Lizenz erlaubt {license_info.max_users} aktive Nutzer, aktuell {active} aktiv. "
            "Ein neuer aktiver Nutzer über dem Limit hinaus wird abgelehnt."
        )

    def _check_active_user_limit(self, additional_active_users: int = 1) -> None:
        """Enforce the license's active-user limit for new or reactivated users.

        No-ops without a loaded license so missing/invalid licenses (handled
        separately as a soft startup warning) don't also block user management.
        """
        license_info = self.license_result.license_info
        if license_info is None:
            return
        projected = self.repository.active_user_count() + additional_active_users
        if projected > license_info.max_users:
            raise ValueError(
                f"Lizenz erlaubt maximal {license_info.max_users} aktive Nutzer; "
                f"mit dieser Aktion wären es {projected}. Deaktivieren Sie zuerst einen anderen "
                "Nutzer oder erweitern Sie die Lizenz."
            )

    def _open_create_user_dialog(self, parent: tk.Misc, *, on_saved) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Benutzer anlegen")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        values = {
            "username": tk.StringVar(),
            "display_name": tk.StringVar(),
            "role": tk.StringVar(value=ROLE_LABELS[UserRole.PLANNER]),
            "password": tk.StringVar(),
            "repeat": tk.StringVar(),
        }
        tk.Label(dialog, text="Neuen Benutzer anlegen", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))
        row = 1
        for key, label, show in [
            ("username", "Benutzername", ""),
            ("display_name", "Anzeigename", ""),
            ("password", "Passwort", "*"),
            ("repeat", "Passwort wiederholen", "*"),
        ]:
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=6)
            ttk.Entry(dialog, textvariable=values[key], width=32, show=show).grid(row=row, column=1, padx=18, pady=6)
            row += 1
        tk.Label(dialog, text="Rolle", bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=6)
        ttk.Combobox(dialog, textvariable=values["role"], values=list(ROLE_LABELS.values()), state="readonly", width=29).grid(row=row, column=1, padx=18, pady=6)
        row += 1

        seat_hint = self._license_seat_hint()
        if seat_hint is not None:
            tk.Label(dialog, text=seat_hint, bg="#FFFFFF", fg="#B45309", wraplength=340, justify="left").grid(row=row, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 8))
            row += 1

        def create() -> None:
            if values["password"].get() != values["repeat"].get():
                messagebox.showerror("Anlegen fehlgeschlagen", "Die Passwörter stimmen nicht überein.", parent=dialog)
                return
            try:
                self._check_active_user_limit()
                self.repository.create_user(
                    values["username"].get(),
                    values["password"].get(),
                    ROLE_BY_LABEL[values["role"].get()],
                    values["display_name"].get(),
                    user_id=self._current_user_id(),
                )
                dialog.destroy()
                on_saved()
            except ValueError as exc:
                messagebox.showerror("Anlegen fehlgeschlagen", str(exc), parent=dialog)

        ttk.Button(dialog, text="Anlegen", style="Primary.TButton", command=create).grid(row=row, column=1, sticky="e", padx=18, pady=(6, 18))
        return dialog

    def _open_role_dialog(self, parent: tk.Misc, user: User, *, on_saved) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Rolle ändern")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        tk.Label(dialog, text=f"Rolle für {user.display_name}", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))
        role_value = tk.StringVar(value=ROLE_LABELS.get(user.role, user.role.value))
        tk.Label(dialog, text="Neue Rolle", bg="#FFFFFF", fg="#334155").grid(row=1, column=0, sticky="w", padx=18, pady=6)
        ttk.Combobox(dialog, textvariable=role_value, values=list(ROLE_LABELS.values()), state="readonly", width=29).grid(row=1, column=1, padx=18, pady=6)

        def save_role() -> None:
            try:
                self.repository.update_user_role(user.id, ROLE_BY_LABEL[role_value.get()], user_id=self._current_user_id())
                dialog.destroy()
                on_saved()
            except ValueError as exc:
                messagebox.showerror("Rolle ändern fehlgeschlagen", str(exc), parent=dialog)

        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_role).grid(row=2, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog

    def _open_password_reset_dialog(self, parent: tk.Misc, user: User) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Passwort zurücksetzen")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        tk.Label(dialog, text=f"Neues Passwort für {user.display_name}", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))
        password = tk.StringVar()
        repeat = tk.StringVar()
        for row, (label, variable) in enumerate([("Neues Passwort", password), ("Wiederholen", repeat)], start=1):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=6)
            ttk.Entry(dialog, textvariable=variable, width=32, show="*").grid(row=row, column=1, padx=18, pady=6)

        def save_password() -> None:
            if password.get() != repeat.get():
                messagebox.showerror("Zurücksetzen fehlgeschlagen", "Die Passwörter stimmen nicht überein.", parent=dialog)
                return
            try:
                self.repository.admin_reset_password(user.id, password.get(), user_id=self._current_user_id())
                dialog.destroy()
            except ValueError as exc:
                messagebox.showerror("Zurücksetzen fehlgeschlagen", str(exc), parent=dialog)

        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_password).grid(row=3, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog


def create_app(
    database_path: str | Path | None = None,
    license_path: str | Path | None = None,
) -> AuthenticatedSchedulerApp:
    repository = SQLiteSchedulerRepository(database_path or default_database_path())
    service = repository.load()
    active_user_count = repository.active_user_count()
    license_result = LicenseManager(license_path).check(current_user_count=active_user_count)
    return AuthenticatedSchedulerApp(service, repository, license_result=license_result)


def main() -> None:
    app = create_app()
    app.mainloop()
