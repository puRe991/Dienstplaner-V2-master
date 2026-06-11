from __future__ import annotations

import calendar
import sqlite3
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .licensing import LicenseCheckResult, LicenseManager
from .models import DEFAULT_ABSENCE_REASONS, Absence, Employee, ExportFormat, RuleProfile, Shift
from .repository import SQLiteSchedulerRepository
from .services import DEFAULT_RETAIL_DEPARTMENTS, ForecastImportService, SchedulerService


@dataclass(frozen=True)
class ShiftStyle:
    background: str
    foreground: str
    label: str


SHIFT_STYLES: dict[str, ShiftStyle] = {
    "frühschicht": ShiftStyle("#DCF8DF", "#12713A", "Frühschicht"),
    "spätschicht": ShiftStyle("#FDEBD2", "#B45309", "Spätschicht"),
    "nachtschicht": ShiftStyle("#DCEAFE", "#0B4DB3", "Nachtschicht"),
    "bereitschaft": ShiftStyle("#EEE0FF", "#7E22CE", "Bereitschaft"),
}


class SchedulerApp(tk.Tk):
    """Modern desktop shell for the standalone Python scheduler.

    The UI mirrors the provided dashboard layout while keeping every action wired to
    the existing service and SQLite repository. It intentionally uses only the
    Python standard library so the application starts on a clean Python install.
    """

    GERMAN_WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    GERMAN_WEEKDAY_ABBR = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    GERMAN_MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    GERMAN_MONTH_ABBR = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    SIDEBAR_WIDTH = 250
    RIGHT_PANEL_WIDTH = 250
    UNASSIGNED_EMPLOYEE_BG = "#FEF3C7"
    UNASSIGNED_EMPLOYEE_FG = "#92400E"
    UNASSIGNED_CELL_BG = "#FFFBEB"

    def __init__(self, service: SchedulerService, repository: SQLiteSchedulerRepository, license_result: LicenseCheckResult | None = None) -> None:
        super().__init__()
        self.service = service
        self.repository = repository
        self.license_result = license_result or LicenseCheckResult(False, "Lizenzprüfung wurde nicht ausgeführt.")
        self.status = tk.StringVar(value="Bereit")
        self.selected_shift_id: str | None = None
        self.week_start = self._default_week_start()
        self.employee_rows: dict[str, int] = {}
        self.schedule_cells: dict[tuple[str, int], tk.Label] = {}
        self.sidebar_buttons: dict[str, tk.Button] = {}
        self.active_view = "Dienstplan"

        self.title("Dienstplanung Pro")
        self.geometry("1440x840")
        self.minsize(1180, 720)
        self.configure(bg="#F8FAFC")
        self._configure_styles()
        self._build_ui()
        self._refresh_all()
        self._apply_license_status()

    @classmethod
    def _default_week_start(cls) -> datetime:
        """Start the planner on the current German calendar week (Monday, 00:00)."""
        return cls._week_start_for_date(datetime.now())

    @staticmethod
    def _week_start_for_date(value: datetime) -> datetime:
        return (value - timedelta(days=value.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#F8FAFC")
        style.configure("Card.TFrame", background="#FFFFFF", relief="flat")
        style.configure("Sidebar.TFrame", background="#FFFFFF")
        style.configure("TLabel", background="#F8FAFC", foreground="#0F172A", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground="#64748B", background="#F8FAFC")
        style.configure("Card.TLabel", background="#FFFFFF", foreground="#0F172A")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), background="#F8FAFC")
        style.configure("Sidebar.TLabel", background="#FFFFFF", foreground="#0F172A", font=("Segoe UI", 11))
        style.configure("SidebarActive.TLabel", background="#EAF2FF", foreground="#0B66E4", font=("Segoe UI", 11, "bold"))
        style.configure("Primary.TButton", background="#0B66E4", foreground="#FFFFFF", borderwidth=0, focusthickness=0, padding=(14, 10))
        style.map("Primary.TButton", background=[("active", "#0958C7")], foreground=[("active", "#FFFFFF")])
        style.configure("Ghost.TButton", background="#FFFFFF", foreground="#334155", padding=(12, 9))
        style.configure("Danger.TButton", background="#FFFFFF", foreground="#DC2626", padding=(12, 9))

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_header()
        self._build_sidebar()
        self._build_content()
        self._build_footer()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg="#FFFFFF", height=62, highlightbackground="#E2E8F0", highlightthickness=1)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(1, weight=1)

        logo = tk.Label(header, text="▣", bg="#0B66E4", fg="#FFFFFF", font=("Segoe UI", 16, "bold"), width=2)
        logo.grid(row=0, column=0, padx=(22, 10), pady=14)
        tk.Label(header, text="Dienstplanung Pro", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 16, "bold")).grid(row=0, column=1, sticky="w")

        self.search_term = tk.StringVar()
        search = ttk.Entry(header, textvariable=self.search_term, width=46)
        search.grid(row=0, column=2, padx=20, ipady=7)
        search.insert(0, "Suche nach Mitarbeitenden, Schichten...")
        search.bind("<FocusIn>", self._clear_search_placeholder)
        search.bind("<Return>", lambda _event: self._apply_search())

        self.notification_label = tk.Label(header, text="Offene Slots: 0", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 12))
        self.notification_label.grid(row=0, column=3, padx=(12, 24))
        self.license_label = tk.Label(header, text="Lizenz wird geprüft", bg="#FFFFFF", fg="#0F172A", justify="left", font=("Segoe UI", 10))
        self.license_label.grid(row=0, column=4, padx=(0, 24))


    def _apply_license_status(self) -> None:
        color = "#15803D" if self.license_result.valid else "#B91C1C"
        prefix = "Lizenz gültig" if self.license_result.valid else "Lizenzproblem"
        if hasattr(self, "license_label"):
            self.license_label.configure(
                text=f"{prefix}\n{self.license_result.company_name}",
                fg=color,
            )
        self._set_status(f"{prefix}: {self.license_result.display_text} — {self.license_result.message}")

    def _build_sidebar(self) -> None:
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=self.SIDEBAR_WIDTH)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        navigation = [
            ("Dashboard", "⌂  Dashboard", self._show_dashboard),
            ("Dienstplan", "▣  Dienstplan", self._show_schedule),
            ("Mitarbeiter", "👥  Mitarbeiter", self._open_employee_manager),
            ("Abteilungen", "▦  Abteilungen", self._open_department_manager),
            ("Abwesenheiten", "☂  Abwesenheiten", self._open_absence_manager),
            ("Schichten", "◷  Schichten", self._open_shift_manager),
            ("Berichte", "▥  Berichte", self._open_reports_window),
            ("Änderungsverlauf", "⏱  Änderungsverlauf", self._open_audit_log_window),
            ("Einstellungen", "⚙  Einstellungen", self._open_settings_window),
        ]
        for index, (key, text, command) in enumerate(navigation):
            button = tk.Button(
                sidebar,
                text=text,
                anchor="w",
                borderwidth=0,
                cursor="hand2",
                font=("Segoe UI", 11, "bold" if key == self.active_view else "normal"),
                bg="#EAF2FF" if key == self.active_view else "#FFFFFF",
                fg="#0B66E4" if key == self.active_view else "#0F172A",
                activebackground="#EAF2FF",
                activeforeground="#0B66E4",
                padx=24,
                pady=12,
                command=lambda item_key=key, item_command=command: self._activate_sidebar(item_key, item_command),
            )
            button.grid(row=index, column=0, sticky="ew", padx=14, pady=(8 if index == 0 else 0, 0))
            self.sidebar_buttons[key] = button

        sidebar.rowconfigure(8, weight=1)
        card = tk.Frame(sidebar, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        card.grid(row=9, column=0, sticky="ew", padx=20, pady=20)
        tk.Label(card, text="🌙  Nächste Schicht", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(16, 12))
        self.next_shift_time_label = tk.Label(card, text="Keine Schicht geplant", bg="#FFFFFF", fg="#0F172A")
        self.next_shift_time_label.pack(anchor="w", padx=18)
        self.next_shift_name_label = tk.Label(card, text="Offen", bg="#E2E8F0", fg="#334155", font=("Segoe UI", 9, "bold"))
        self.next_shift_name_label.pack(anchor="w", padx=18, pady=8)
        self.next_shift_branch_label = tk.Label(card, text="Standort\n–", bg="#FFFFFF", fg="#475569", justify="left")
        self.next_shift_branch_label.pack(anchor="w", padx=18, pady=(16, 18))
        tk.Label(sidebar, text="© 2026 Dienstplanung Pro", bg="#FFFFFF", fg="#64748B").grid(row=10, column=0, sticky="w", padx=24, pady=(0, 16))

    def _build_content(self) -> None:
        content = ttk.Frame(self, padding=(28, 20, 22, 16))
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, minsize=self.RIGHT_PANEL_WIDTH)
        content.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(content)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        toolbar.columnconfigure(2, weight=1)
        ttk.Label(toolbar, text="Dienstplan", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(toolbar, text="‹", style="Ghost.TButton", command=lambda: self._move_week(-7)).grid(row=0, column=1, padx=(28, 0))
        self.week_label = ttk.Label(toolbar, text="", style="Card.TLabel", padding=(18, 9))
        self.week_label.grid(row=0, column=2, sticky="w")
        ttk.Button(toolbar, text="›", style="Ghost.TButton", command=lambda: self._move_week(7)).grid(row=0, column=3, padx=(0, 20))
        ttk.Button(toolbar, text="+ Schicht hinzufügen", style="Primary.TButton", command=self._open_shift_dialog).grid(row=0, column=4, padx=6)

        self.cards_frame = ttk.Frame(content)
        self.cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for column in range(4):
            self.cards_frame.columnconfigure(column, weight=1)

        main_area = ttk.Frame(content)
        main_area.grid(row=2, column=0, sticky="nsew", padx=(0, 14))
        main_area.columnconfigure(0, weight=1)
        main_area.rowconfigure(0, weight=1)
        self._build_schedule_grid(main_area)
        self._build_legend_and_details(main_area)
        self._build_right_panel(content)

    def _build_schedule_grid(self, parent: ttk.Frame) -> None:
        self.grid_container = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        self.grid_container.grid(row=0, column=0, sticky="nsew")
        self.grid_container.rowconfigure(0, weight=1)
        self.grid_container.columnconfigure(0, weight=1)

        self.grid_canvas = tk.Canvas(self.grid_container, bg="#FFFFFF", highlightthickness=0)
        horizontal_scrollbar = ttk.Scrollbar(self.grid_container, orient="horizontal", command=self.grid_canvas.xview)
        vertical_scrollbar = ttk.Scrollbar(self.grid_container, orient="vertical", command=self.grid_canvas.yview)
        self.grid_canvas.configure(xscrollcommand=horizontal_scrollbar.set, yscrollcommand=vertical_scrollbar.set)
        self.grid_canvas.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        self.grid_frame = tk.Frame(self.grid_canvas, bg="#FFFFFF")
        self.grid_canvas_window = self.grid_canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", self._update_schedule_scroll_region)
        self.grid_canvas.bind("<Configure>", self._resize_schedule_canvas_window)
        self.grid_canvas.bind("<Shift-MouseWheel>", self._scroll_schedule_horizontally)

        self.grid_frame.columnconfigure(0, minsize=160)
        for column in range(1, 8):
            self.grid_frame.columnconfigure(column, weight=1, minsize=115)

    def _build_legend_and_details(self, parent: ttk.Frame) -> None:
        self.legend_frame = ttk.Frame(parent)
        self.legend_frame.grid(row=1, column=0, sticky="ew", pady=(14, 10))

        details = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        details.grid(row=2, column=0, sticky="ew")
        details.columnconfigure(1, weight=1)
        self.detail_title = tk.Label(details, text="Schichtdetails", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 11, "bold"))
        self.detail_title.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))
        self.detail_body = tk.Label(details, text="Bitte eine Schicht auswählen.", bg="#FFFFFF", fg="#334155", justify="left")
        self.detail_body.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))
        ttk.Button(details, text="Bearbeiten", style="Ghost.TButton", command=self._open_shift_dialog_for_selected).grid(row=1, column=2, padx=4, pady=14)
        ttk.Button(details, text="Kopieren", style="Ghost.TButton", command=self._open_copy_shift_dialog_for_selected).grid(row=1, column=3, padx=4, pady=14)
        ttk.Button(details, text="Zuweisen", style="Ghost.TButton", command=self._open_assignment_dialog).grid(row=1, column=4, padx=4, pady=14)
        ttk.Button(details, text="Löschen", style="Danger.TButton", command=self._delete_selected_shift).grid(row=1, column=5, padx=(4, 18), pady=14)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        right = ttk.Frame(parent)
        right.grid(row=1, column=1, rowspan=2, sticky="nsew")
        right.columnconfigure(0, weight=1)
        self.calendar_frame = tk.Frame(right, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        self.calendar_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.absence_frame = tk.Frame(right, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        self.absence_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        actions = tk.Frame(right, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        actions.grid(row=2, column=0, sticky="ew")
        tk.Label(actions, text="Schnellaktionen", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        for text, command in [
            ("👥 Mitarbeiter anlegen", self._open_employee_dialog),
            ("▦  Abteilung anlegen", self._open_department_dialog),
            ("☂ Abwesenheit erfassen", self._open_absence_dialog),
            ("➕ Mitarbeitenden zuweisen", self._open_assignment_dialog),
            ("▤  Schicht anlegen", self._open_shift_dialog),
            ("✈  Dienstplan veröffentlichen", self._publish_schedule),
            ("📈 Forecast importieren", self._import_forecast),
        ]:
            ttk.Button(actions, text=text, style="Ghost.TButton", command=command).pack(fill="x", padx=12, pady=5)
        ttk.Button(actions, text="💾 Speichern", style="Ghost.TButton", command=self._save).pack(fill="x", padx=12, pady=(5, 12))
        ttk.Button(actions, text="CSV Export", style="Ghost.TButton", command=self._export_csv).pack(fill="x", padx=12, pady=(0, 12))

    def _activate_sidebar(self, key: str, command: object) -> None:
        self.active_view = key
        for item_key, button in self.sidebar_buttons.items():
            is_active = item_key == key
            button.configure(
                bg="#EAF2FF" if is_active else "#FFFFFF",
                fg="#0B66E4" if is_active else "#0F172A",
                font=("Segoe UI", 11, "bold" if is_active else "normal"),
            )
        if callable(command):
            command()

    def _show_dashboard(self) -> None:
        self.week_start = self._default_week_start()
        self.selected_shift_id = None
        self._refresh_all()
        self._set_status("Dashboard für die aktuelle Woche aktualisiert.")

    def _show_schedule(self) -> None:
        self.week_start = self._default_week_start()
        self.selected_shift_id = None
        self._refresh_all()
        self._set_status("Dienstplanansicht für die aktuelle Woche geöffnet.")

    def _open_employee_manager(self) -> None:
        window = self._create_manager_window("Mitarbeiter verwalten", "1040x540")
        columns = ("name", "department", "qualification", "hours", "break", "branch", "wage", "active")
        tree = self._create_tree(window, columns, {
            "name": "Name",
            "department": "Abteilung",
            "qualification": "Qualifikation",
            "hours": "Wochenstunden",
            "break": "Pause/Schicht",
            "branch": "Filiale",
            "wage": "Stundenlohn",
            "active": "Status",
        })

        def refresh() -> None:
            self._clear_tree(tree)
            for employee in sorted(self.service.employees, key=lambda item: item.name):
                tree.insert("", "end", iid=employee.id, values=(
                    employee.name,
                    employee.department,
                    employee.qualification or "-",
                    employee.weekly_hours_limit,
                    f"{employee.break_minutes_per_shift} Min",
                    employee.branch,
                    f"{employee.hourly_wage:.2f}",
                    "Aktiv" if employee.is_active else "Inaktiv",
                ))

        def selected_employee() -> Employee | None:
            selection = tree.selection()
            return self.service.find_employee(selection[0]) if selection else None

        def add() -> None:
            dialog = self._open_employee_dialog()
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def edit() -> None:
            employee = selected_employee()
            if employee is None:
                self._set_status("Bitte einen Mitarbeiter auswählen.")
                return
            dialog = self._open_employee_dialog(employee)
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def delete() -> None:
            employee = selected_employee()
            if employee is None:
                self._set_status("Bitte einen Mitarbeiter auswählen.")
                return
            if messagebox.askyesno("Mitarbeiter löschen", f"Soll {employee.name} wirklich gelöscht werden?", parent=window):
                self.service.delete_employee(employee.id, user_id=self._current_user_id())
                self._persist_changes("Mitarbeiter gelöscht.", window)
                self._refresh_all()
                refresh()

        self._add_manager_buttons(window, [("Neu", add), ("Bearbeiten", edit), ("Löschen", delete), ("Aktualisieren", refresh)])
        tree.bind("<Double-Button-1>", lambda _event: edit())
        refresh()


    def _open_audit_log_window(self) -> None:
        window = self._create_manager_window("Änderungsverlauf", "1180x560")
        columns = ("timestamp", "user", "action", "entity", "entity_id", "before", "after")
        tree = self._create_tree(window, columns, {
            "timestamp": "Zeitpunkt",
            "user": "Benutzer",
            "action": "Aktion",
            "entity": "Objekt",
            "entity_id": "Objekt-ID",
            "before": "Vorher",
            "after": "Nachher",
        })
        tree.column("before", width=230)
        tree.column("after", width=230)

        def compact(value: str) -> str:
            normalized = " ".join(value.split())
            return normalized[:117] + "..." if len(normalized) > 120 else normalized

        def refresh() -> None:
            self._clear_tree(tree)
            events = self.repository.list_audit_events(500)
            if not events:
                events = self.service.audit_trail(500)
            for event in events:
                tree.insert("", "end", iid=event.id, values=(
                    event.timestamp.strftime("%d.%m.%Y %H:%M:%S"),
                    event.user_id,
                    event.action,
                    event.entity_type,
                    event.entity_id,
                    compact(event.before),
                    compact(event.after),
                ))
            self._set_status(f"Änderungsverlauf geladen: {len(events)} Einträge.")

        def show_details() -> None:
            selection = tree.selection()
            if not selection:
                self._set_status("Bitte einen Audit-Eintrag auswählen.")
                return
            event_id = selection[0]
            event = next((item for item in self.repository.list_audit_events(1000) if item.id == event_id), None)
            if event is None:
                event = next((item for item in self.service.audit_events if item.id == event_id), None)
            if event is None:
                self._set_status("Audit-Eintrag wurde nicht gefunden.")
                return
            detail = tk.Toplevel(window)
            detail.title("Audit-Eintrag")
            detail.transient(window)
            detail.configure(bg="#FFFFFF")
            text = tk.Text(detail, width=120, height=28, wrap="word")
            text.pack(fill="both", expand=True, padx=12, pady=12)
            text.insert("end", f"Zeitpunkt: {event.timestamp.isoformat()}\nBenutzer: {event.user_id}\nAktion: {event.action}\nObjekt: {event.entity_type} {event.entity_id}\n\nVorher:\n{event.before or '-'}\n\nNachher:\n{event.after or '-'}")
            text.configure(state="disabled")

        self._add_manager_buttons(window, [("Details", show_details), ("Aktualisieren", refresh)])
        tree.bind("<Double-Button-1>", lambda _event: show_details())
        refresh()

    def _current_user_id(self) -> str:
        return "local"

    def _open_department_manager(self) -> None:
        window = self._create_manager_window("Abteilungen verwalten", "620x480")
        columns = ("name", "employees", "shifts", "source")
        tree = self._create_tree(window, columns, {
            "name": "Abteilung",
            "employees": "Mitarbeitende",
            "shifts": "Schichten",
            "source": "Typ",
        })

        def refresh() -> None:
            self._clear_tree(tree)
            default_names = {department.lower() for department in DEFAULT_RETAIL_DEPARTMENTS}
            for department in self.service.department_options():
                employee_count = sum(1 for employee in self.service.employees if employee.department.lower() == department.lower())
                shift_count = sum(1 for shift in self.service.shifts if shift.department.lower() == department.lower())
                source = "Standard" if department.lower() in default_names else "Eigene"
                tree.insert("", "end", iid=department, values=(department, employee_count, shift_count, source))

        def add() -> None:
            self._open_department_dialog(parent=window, refresh_callback=refresh)

        def delete() -> None:
            selection = tree.selection()
            if not selection:
                self._set_status("Bitte eine Abteilung auswählen.")
                return
            department = selection[0]
            if not messagebox.askyesno("Abteilung löschen", f"Soll '{department}' wirklich gelöscht werden?", parent=window):
                return
            try:
                if self.service.delete_department(department):
                    self._persist_changes("Abteilung gelöscht.", window)
                    self._refresh_all()
                    refresh()
            except ValueError as exc:
                messagebox.showerror("Abteilung kann nicht gelöscht werden", str(exc), parent=window)

        self._add_manager_buttons(window, [("Neu", add), ("Löschen", delete), ("Aktualisieren", refresh)])
        refresh()

    def _open_absence_manager(self) -> None:
        window = self._create_manager_window("Abwesenheiten verwalten", "820x500")
        columns = ("employee", "start", "end", "reason")
        tree = self._create_tree(window, columns, {"employee": "Mitarbeiter", "start": "Start", "end": "Ende", "reason": "Grund"})

        def refresh() -> None:
            self._clear_tree(tree)
            for employee in sorted(self.service.employees, key=lambda item: item.name):
                for absence in sorted(employee.absences, key=lambda item: item.start):
                    tree.insert("", "end", iid=absence.id, values=(employee.name, f"{absence.start:%d.%m.%Y %H:%M}", f"{absence.end:%d.%m.%Y %H:%M}", absence.reason or "-"))

        def add() -> None:
            dialog = self._open_absence_dialog()
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def delete() -> None:
            selection = tree.selection()
            if not selection:
                self._set_status("Bitte eine Abwesenheit auswählen.")
                return
            if messagebox.askyesno("Abwesenheit löschen", "Soll die Abwesenheit gelöscht werden?", parent=window):
                self.service.delete_absence(selection[0])
                self._persist_changes("Abwesenheit gelöscht.", window)
                self._refresh_all()
                refresh()

        self._add_manager_buttons(window, [("Neu", add), ("Löschen", delete), ("Aktualisieren", refresh)])
        tree.bind("<Double-Button-1>", lambda _event: delete())
        refresh()

    def _open_shift_manager(self) -> None:
        window = self._create_manager_window("Schichten verwalten", "980x520")
        columns = ("name", "department", "start", "end", "capacity", "branch", "employees")
        tree = self._create_tree(window, columns, {
            "name": "Name",
            "department": "Abteilung",
            "start": "Start",
            "end": "Ende",
            "capacity": "Besetzung",
            "branch": "Filiale",
            "employees": "Mitarbeitende",
        })

        def refresh() -> None:
            self._clear_tree(tree)
            for shift in sorted(self.service.shifts, key=lambda item: (item.start, item.name)):
                tree.insert("", "end", iid=shift.id, values=(
                    shift.name,
                    shift.department,
                    f"{shift.start:%d.%m.%Y %H:%M}",
                    f"{shift.end:%d.%m.%Y %H:%M}",
                    f"{len(shift.employee_ids)}/{shift.required_employees}",
                    shift.branch,
                    ", ".join(shift.employee_names) or "-",
                ))

        def selected_shift() -> Shift | None:
            selection = tree.selection()
            return self.service.find_shift(selection[0]) if selection else None

        def add() -> None:
            dialog = self._open_shift_dialog()
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def edit() -> None:
            shift = selected_shift()
            if shift is None:
                self._set_status("Bitte eine Schicht auswählen.")
                return
            self.selected_shift_id = shift.id
            dialog = self._open_shift_dialog(shift)
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def assign() -> None:
            shift = selected_shift()
            if shift is not None:
                self.selected_shift_id = shift.id
            dialog = self._open_assignment_dialog(preselected_shift_id=self.selected_shift_id)
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def copy() -> None:
            shift = selected_shift()
            if shift is None:
                self._set_status("Bitte eine Schicht auswählen.")
                return
            self.selected_shift_id = shift.id
            dialog = self._open_copy_shift_dialog(shift)
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def unassign() -> None:
            shift = selected_shift()
            if shift is None or not shift.employee_ids:
                self._set_status("Bitte eine besetzte Schicht auswählen.")
                return
            employee_id = shift.employee_ids[-1]
            self.service.unassign(employee_id, shift.id)
            self._persist_changes("Letzte Zuweisung entfernt.", window)
            self._refresh_all()
            refresh()

        def delete() -> None:
            shift = selected_shift()
            if shift is None:
                self._set_status("Bitte eine Schicht auswählen.")
                return
            self.selected_shift_id = shift.id
            self._delete_selected_shift(parent=window, refresh_callback=refresh)

        self._add_manager_buttons(window, [("Neu", add), ("Bearbeiten", edit), ("Kopieren", copy), ("Zuweisen", assign), ("Zuweisung entfernen", unassign), ("Löschen", delete), ("Aktualisieren", refresh)])
        tree.bind("<Double-Button-1>", lambda _event: edit())
        refresh()

    def _open_reports_window(self) -> None:
        window = self._create_manager_window("Berichte", "760x420")
        columns = ("category", "name", "value", "note")
        tree = self._create_tree(window, columns, {"category": "Kategorie", "name": "Kennzahl", "value": "Wert", "note": "Hinweis"})

        def refresh() -> None:
            self._clear_tree(tree)
            for index, metric in enumerate(self.service.create_reports()):
                tree.insert("", "end", iid=str(index), values=(metric.category, metric.name, metric.value, metric.note))

        self._add_manager_buttons(window, [("Aktualisieren", refresh), ("Report CSV Export", self._export_reports_csv)])
        refresh()

    def _open_settings_window(self) -> None:
        window = self._create_manager_window("Einstellungen · Regelprofile", "980x520")
        info = tk.Label(
            window,
            text=f"SQLite-Datenbank: {self.repository.database_path}\nRegelprofile steuern harte Verstöße und Warnungen für Zuweisungen.",
            bg="#F8FAFC",
            fg="#334155",
            justify="left",
        )
        info.pack(fill="x", padx=16, pady=(14, 6))
        columns = ("active", "name", "rest", "daily", "breaks", "hard", "warnings")
        tree = self._create_tree(window, columns, {
            "active": "Aktiv",
            "name": "Profil",
            "rest": "Ruhezeit",
            "daily": "Tag max.",
            "breaks": "Pausen",
            "hard": "Harte Regeln",
            "warnings": "Warnungen",
        })

        def profile_policy_text(profile: RuleProfile, hard: bool) -> str:
            labels = [
                ("Woche", profile.weekly_hours_limit_is_hard),
                ("Tag", profile.daily_hours_limit_is_hard),
                ("Ruhe", profile.rest_time_is_hard),
                ("Profil", profile.profile_mismatch_is_hard),
                ("Verfügbarkeit", profile.missing_availability_is_hard),
                ("Pause", profile.insufficient_break_is_hard),
            ]
            selected = [label for label, is_hard in labels if is_hard is hard]
            return ", ".join(selected) or "-"

        def refresh() -> None:
            self._clear_tree(tree)
            for profile in sorted(self.service.rule_profiles, key=lambda item: (not item.is_active, item.name.casefold())):
                tree.insert("", "end", iid=profile.id, values=(
                    "Ja" if profile.is_active else "Nein",
                    profile.name,
                    f"{profile.min_rest_hours:g} h",
                    f"{profile.max_daily_hours:g} h",
                    f">6h {profile.break_after_six_hours_minutes} Min / >9h {profile.break_after_nine_hours_minutes} Min",
                    profile_policy_text(profile, True),
                    profile_policy_text(profile, False),
                ))

        def selected_profile() -> RuleProfile | None:
            selection = tree.selection()
            return self.service.find_rule_profile(selection[0]) if selection else None

        def add() -> None:
            dialog = self._open_rule_profile_dialog(parent=window)
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def edit() -> None:
            profile = selected_profile()
            if profile is None:
                self._set_status("Bitte ein Regelprofil auswählen.")
                return
            dialog = self._open_rule_profile_dialog(profile, window)
            if dialog is not None:
                window.wait_window(dialog)
            refresh()

        def activate() -> None:
            profile = selected_profile()
            if profile is None:
                self._set_status("Bitte ein Regelprofil auswählen.")
                return
            self.service.set_active_rule_profile(profile.id)
            if self._persist_changes(f"Regelprofil '{profile.name}' aktiviert.", window):
                refresh()

        def delete() -> None:
            profile = selected_profile()
            if profile is None:
                self._set_status("Bitte ein Regelprofil auswählen.")
                return
            if not messagebox.askyesno("Regelprofil löschen", f"Soll '{profile.name}' gelöscht werden?", parent=window):
                return
            try:
                self.service.delete_rule_profile(profile.id)
                if self._persist_changes("Regelprofil gelöscht.", window):
                    refresh()
            except ValueError as exc:
                messagebox.showerror("Regelprofil kann nicht gelöscht werden", str(exc), parent=window)

        self._add_manager_buttons(window, [("Neu", add), ("Bearbeiten", edit), ("Aktivieren", activate), ("Löschen", delete), ("Jetzt speichern", self._save), ("Dienstplan CSV Export", self._export_csv)])
        tree.bind("<Double-Button-1>", lambda _event: edit())
        refresh()

    def _open_rule_profile_dialog(self, profile: RuleProfile | None = None, parent: tk.Misc | None = None) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Regelprofil bearbeiten" if profile else "Regelprofil anlegen")
        dialog.transient(parent or self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        source = profile or self.service.active_rule_profile
        values = {
            "name": tk.StringVar(value=(profile.name if profile else f"{source.name} Kopie")),
            "rest": tk.StringVar(value=f"{source.min_rest_hours:g}"),
            "daily": tk.StringVar(value=f"{source.max_daily_hours:g}"),
            "break6": tk.StringVar(value=str(source.break_after_six_hours_minutes)),
            "break9": tk.StringVar(value=str(source.break_after_nine_hours_minutes)),
            "active": tk.BooleanVar(value=source.is_active if profile else False),
            "weekly_hard": tk.BooleanVar(value=source.weekly_hours_limit_is_hard),
            "daily_hard": tk.BooleanVar(value=source.daily_hours_limit_is_hard),
            "rest_hard": tk.BooleanVar(value=source.rest_time_is_hard),
            "profile_hard": tk.BooleanVar(value=source.profile_mismatch_is_hard),
            "availability_hard": tk.BooleanVar(value=source.missing_availability_is_hard),
            "break_hard": tk.BooleanVar(value=source.insufficient_break_is_hard),
        }
        fields = [("name", "Name"), ("rest", "Mindestruhezeit (Stunden)"), ("daily", "Max. Tagesarbeitszeit (Stunden)"), ("break6", "Pause bei > 6h (Minuten)"), ("break9", "Pause bei > 9h (Minuten)")]
        for row, (key, label) in enumerate(fields):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
            ttk.Entry(dialog, textvariable=values[key], width=34).grid(row=row, column=1, padx=18, pady=7)
        ttk.Checkbutton(dialog, text="Als aktives Profil verwenden", variable=values["active"]).grid(row=5, column=1, sticky="w", padx=18, pady=(4, 8))
        tk.Label(dialog, text="Harte Regelverstöße", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).grid(row=6, column=0, sticky="w", padx=18, pady=(8, 4))
        checks = [("weekly_hard", "Wochenstundenlimit"), ("daily_hard", "Tageshöchstarbeitszeit"), ("rest_hard", "Ruhezeit"), ("profile_hard", "Abteilung/Filiale/Qualifikation"), ("availability_hard", "Fehlende Verfügbarkeit"), ("break_hard", "Unzureichende Pause")]
        for offset, (key, label) in enumerate(checks, start=7):
            ttk.Checkbutton(dialog, text=label, variable=values[key]).grid(row=offset, column=1, sticky="w", padx=18, pady=2)

        def save_profile() -> None:
            try:
                updated = RuleProfile(
                    name=values["name"].get(),
                    min_rest_hours=float(values["rest"].get().replace(",", ".")),
                    max_daily_hours=float(values["daily"].get().replace(",", ".")),
                    break_after_six_hours_minutes=int(values["break6"].get()),
                    break_after_nine_hours_minutes=int(values["break9"].get()),
                    weekly_hours_limit_is_hard=values["weekly_hard"].get(),
                    daily_hours_limit_is_hard=values["daily_hard"].get(),
                    rest_time_is_hard=values["rest_hard"].get(),
                    profile_mismatch_is_hard=values["profile_hard"].get(),
                    missing_availability_is_hard=values["availability_hard"].get(),
                    insufficient_break_is_hard=values["break_hard"].get(),
                    is_active=values["active"].get(),
                )
                if profile is None:
                    self.service.add_rule_profile(updated)
                else:
                    self.service.update_rule_profile(profile.id, updated)
                if not self._persist_changes("Regelprofil gespeichert.", dialog):
                    return
                dialog.destroy()
            except ValueError as exc:
                messagebox.showerror("Ungültiges Regelprofil", str(exc), parent=dialog)

        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_profile).grid(row=13, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog

    def _create_manager_window(self, title: str, geometry: str) -> tk.Toplevel:
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry(geometry)
        window.transient(self)
        window.configure(bg="#F8FAFC")
        return window

    def _create_tree(self, parent: tk.Toplevel, columns: tuple[str, ...], headings: dict[str, str]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, minwidth=90, width=130, stretch=True)
        tree.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        return tree

    def _add_manager_buttons(self, parent: tk.Toplevel, buttons: list[tuple[str, object]]) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=16, pady=(0, 16))
        for text, command in buttons:
            if callable(command):
                ttk.Button(frame, text=text, style="Ghost.TButton", command=command).pack(side="left", padx=(0, 8))

    @staticmethod
    def _clear_tree(tree: ttk.Treeview) -> None:
        for item_id in tree.get_children():
            tree.delete(item_id)

    def _open_department_dialog(self, parent: tk.Misc | None = None, refresh_callback: object | None = None) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Abteilung hinzufügen")
        dialog.transient(parent or self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        value = tk.StringVar()
        tk.Label(dialog, text="Name", bg="#FFFFFF", fg="#334155").grid(row=0, column=0, sticky="w", padx=18, pady=12)
        entry = ttk.Entry(dialog, textvariable=value, width=36)
        entry.grid(row=0, column=1, padx=18, pady=12)
        entry.focus_set()

        def save_department() -> None:
            try:
                created = self.service.add_department(value.get())
                if not self._persist_changes(f"Abteilung '{created}' hinzugefügt.", dialog):
                    return
                dialog.destroy()
                self._refresh_all()
                if callable(refresh_callback):
                    refresh_callback()
            except ValueError as exc:
                messagebox.showerror("Ungültige Eingabe", str(exc), parent=dialog)

        entry.bind("<Return>", lambda _event: save_department())
        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_department).grid(row=1, column=1, sticky="e", padx=18, pady=(0, 18))
        return dialog

    def _department_combobox(self, parent: tk.Misc, variable: tk.StringVar, row: int) -> ttk.Combobox:
        combobox = ttk.Combobox(parent, textvariable=variable, values=self.service.department_options(), width=32)
        combobox.grid(row=row, column=1, padx=18, pady=7)
        return combobox

    def _format_week_range(self) -> str:
        week_end = self.week_start + timedelta(days=6)
        if self.week_start.month == week_end.month and self.week_start.year == week_end.year:
            return f"{self.week_start.day}. – {week_end.day}. {self._month_name(self.week_start)} {self.week_start.year}"
        return f"{self._format_date(self.week_start)} – {self._format_date(week_end)}"


    def _refresh_legend(self) -> None:
        for child in self.legend_frame.winfo_children():
            child.destroy()

        items = self._legend_items_for_state(
            self._week_shifts(),
            self._week_absences(),
            unassigned_employees=self._unassigned_employee_count(),
        )
        if not items:
            ttk.Label(self.legend_frame, text="Keine eingetragenen Schichten oder Abwesenheiten in dieser Woche.", style="Muted.TLabel").pack(side="left")
            return

        for color, label in items:
            item = ttk.Frame(self.legend_frame)
            item.pack(side="left", padx=(0, 28))
            tk.Label(item, text="●", fg=color, bg="#F8FAFC", font=("Segoe UI", 14)).pack(side="left")
            ttk.Label(item, text=label, style="Muted.TLabel", justify="left").pack(side="left", padx=(6, 0))

    @classmethod
    def _legend_items_for_state(
        cls,
        week_shifts: list[Shift],
        week_absences: list[Absence],
        unassigned_employees: int = 0,
    ) -> list[tuple[str, str]]:
        """Return legend entries only for objects that exist in the selected week."""
        items: list[tuple[str, str]] = []
        seen_shift_labels: set[str] = set()

        for shift in sorted(week_shifts, key=lambda item: (item.start, item.name)):
            style = cls._style_for_shift(shift)
            label = f"{style.label}\n{cls._legend_time_label(shift)}"
            if label in seen_shift_labels:
                continue
            items.append((style.foreground, label))
            seen_shift_labels.add(label)

        if week_absences:
            items.append(("#F87171", "Abwesend\nEingetragen"))

        if any(len(shift.employee_ids) < shift.required_employees for shift in week_shifts):
            items.append(("#CBD5E1", "Offene Schicht\nNicht besetzt"))

        if unassigned_employees > 0:
            items.append((cls.UNASSIGNED_EMPLOYEE_FG, f"Ohne Schicht\n{unassigned_employees} Mitarbeitende"))

        return items

    @staticmethod
    def _legend_time_label(shift: Shift) -> str:
        if shift.duration_hours >= 23.5:
            return "24h"
        return f"{shift.start:%H:%M} – {shift.end:%H:%M}"

    def _update_schedule_scroll_region(self, _event: tk.Event | None = None) -> None:
        """Keep the planner canvas scrollable when the week grid is wider than the window."""
        self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all"))

    def _resize_schedule_canvas_window(self, event: tk.Event) -> None:
        """Let the grid fill available space while preserving horizontal scrolling for narrow windows."""
        requested_width = self.grid_frame.winfo_reqwidth()
        self.grid_canvas.itemconfigure(self.grid_canvas_window, width=max(event.width, requested_width))
        self._update_schedule_scroll_region()

    def _scroll_schedule_horizontally(self, event: tk.Event) -> None:
        """Support Shift + mouse wheel for the horizontally scrollable weekly planner."""
        if event.delta == 0:
            return
        direction = -1 if event.delta > 0 else 1
        self.grid_canvas.xview_scroll(direction, "units")

    def _refresh_all(self) -> None:
        self.week_label.configure(text=f"📅  {self._format_week_range()}")
        self._refresh_header_state()
        self._refresh_cards()
        self._refresh_legend()
        self._refresh_schedule_grid()
        self._refresh_calendar()
        self._refresh_absences()
        self._refresh_details()

    def _refresh_header_state(self) -> None:
        open_slots = sum(max(0, shift.required_employees - len(shift.employee_ids)) for shift in self._week_shifts())
        current_time = datetime.now()
        upcoming = next((shift for shift in sorted(self.service.shifts, key=lambda item: item.start) if shift.start >= current_time), None)
        self.notification_label.configure(text=f"Offene Slots: {open_slots}")
        if upcoming is None:
            self.next_shift_time_label.configure(text="Keine Schicht geplant")
            self.next_shift_name_label.configure(text="Offen", bg="#E2E8F0", fg="#334155")
            self.next_shift_branch_label.configure(text="Standort\n–")
            return
        style = self._style_for_shift(upcoming)
        self.next_shift_time_label.configure(text=f"{self._format_datetime(upcoming.start)} – {upcoming.end:%H:%M}")
        self.next_shift_name_label.configure(text=upcoming.name, bg=style.background, fg=style.foreground)
        self.next_shift_branch_label.configure(text=f"Standort\n📍  {upcoming.branch}")

    def _refresh_cards(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()
        active_count = sum(1 for employee in self.service.employees if employee.is_active)
        unassigned_count = self._unassigned_employee_count()
        open_shifts = sum(max(0, shift.required_employees - len(shift.employee_ids)) for shift in self._week_shifts())
        absences = sum(1 for employee in self.service.employees for absence in employee.absences if self._range_in_week(absence.start, absence.end))
        hours = self._planned_week_hours()
        avg_hours = hours / max(1, len(self.service.employees))
        employee_note = (
            f"{unassigned_count} ohne Schicht"
            if unassigned_count
            else (f"{len(self.service.employees) - active_count} inaktiv" if len(self.service.employees) != active_count else "Alle geplant")
        )
        cards = [
            ("👥", "Mitarbeiter", str(active_count), employee_note),
            ("▣", "Offene Schichten", str(open_shifts), "Kritisch prüfen" if open_shifts else "Voll besetzt"),
            ("☂", "Abwesenheiten", str(absences), "Erfasst"),
            ("◷", "Stunden diese Woche", f"{hours:.0f} h", f"Ø {avg_hours:.1f} h pro Mitarbeiter"),
        ]
        colors = ["#0B66E4", "#F59E0B", "#22C55E", "#A855F7"]
        for index, (icon, title, value, note) in enumerate(cards):
            card = tk.Frame(self.cards_frame, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 10, 0))
            tk.Label(card, text=icon, bg=colors[index], fg="#FFFFFF", font=("Segoe UI", 16), width=3).grid(row=0, column=0, rowspan=2, padx=16, pady=16)
            tk.Label(card, text=title, bg="#FFFFFF", fg="#475569").grid(row=0, column=1, sticky="w", padx=(0, 18), pady=(16, 0))
            tk.Label(card, text=value, bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 18, "bold")).grid(row=1, column=1, sticky="w", padx=(0, 18))
            tk.Label(card, text=note, bg="#FFFFFF", fg="#0B66E4" if index == 0 else "#475569").grid(row=2, column=1, sticky="w", padx=(0, 18), pady=(0, 14))

    def _refresh_schedule_grid(self) -> None:
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.employee_rows.clear()
        self.schedule_cells.clear()

        headers = ["Mitarbeiter", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        for column, header in enumerate(headers):
            text = header if column == 0 else f"{header}\n{self._format_day_month(self.week_start + timedelta(days=column - 1))}"
            tk.Label(self.grid_frame, text=text, bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 9, "bold"), justify="center", height=3).grid(row=0, column=column, sticky="nsew")

        filtered_employees = self._filtered_employees()
        if not filtered_employees:
            message = "Keine Mitarbeitenden vorhanden. Bitte über Schnellaktionen anlegen." if not self.service.employees else "Keine Mitarbeitenden passend zur Suche."
            tk.Label(self.grid_frame, text=message, bg="#FFFFFF", fg="#64748B", pady=28).grid(row=1, column=0, columnspan=8, sticky="nsew")
            self.grid_frame.update_idletasks()
            self._update_schedule_scroll_region()
            return
        for row_index, employee in enumerate(filtered_employees, start=1):
            self.employee_rows[employee.id] = row_index
            week_shifts = self._employee_week_shifts(employee, self.week_start)
            is_unassigned = self._is_unassigned_for_week(employee, self.week_start)
            employee_text = (
                f"{self._avatar(employee.name)}  {employee.name}\n"
                f"{employee.qualification or employee.department}\n"
                f"● {self._availability_text(employee)} · {self._employee_week_assignment_text(week_shifts)}"
            )
            employee_label = tk.Label(
                self.grid_frame,
                text=employee_text,
                bg=self.UNASSIGNED_EMPLOYEE_BG if is_unassigned else "#FFFFFF",
                fg=self.UNASSIGNED_EMPLOYEE_FG if is_unassigned else "#0F172A",
                justify="left",
                anchor="w",
                padx=14,
                pady=8,
                cursor="hand2",
            )
            employee_label.grid(row=row_index, column=0, sticky="nsew")
            employee_label.bind("<Double-Button-1>", lambda _event, employee_id=employee.id: self._open_employee_dialog(self.service.find_employee(employee_id)))
            for day_index in range(7):
                cell = self._make_schedule_cell(employee, day_index, is_unassigned)
                cell.grid(row=row_index, column=day_index + 1, sticky="nsew", padx=4, pady=5)
                self.schedule_cells[(employee.id, day_index)] = cell

        self.grid_frame.update_idletasks()
        self._update_schedule_scroll_region()

    def _make_schedule_cell(self, employee: Employee, day_index: int, is_unassigned: bool = False) -> tk.Label:
        day = self.week_start.date() + timedelta(days=day_index)
        absence = next((item for item in employee.absences if item.start.date() <= day <= item.end.date()), None)
        if absence is not None:
            return tk.Label(self.grid_frame, text=f"Abwesend\n{absence.reason or 'Abwesenheit'}", bg="#FEE2E2", fg="#DC2626", font=("Segoe UI", 8, "bold"), justify="center")

        shift = next((item for item in employee.shifts if item.start.date() == day), None)
        if shift is None:
            label = tk.Label(
                self.grid_frame,
                text="+\nNicht geplant" if is_unassigned else "+",
                bg=self.UNASSIGNED_CELL_BG if is_unassigned else "#FFFFFF",
                fg=self.UNASSIGNED_EMPLOYEE_FG if is_unassigned else "#94A3B8",
                font=("Segoe UI", 9 if is_unassigned else 12, "bold"),
                justify="center",
                cursor="hand2",
            )
            label.bind("<Button-1>", lambda _event: self._open_assignment_dialog())
            return label
        style = self._style_for_shift(shift)
        label = tk.Label(
            self.grid_frame,
            text=f"{shift.name}\n{shift.start:%H:%M} – {shift.end:%H:%M}\nNetto {employee.net_hours_for_shift(shift):.1f} h · Pause {employee.break_minutes_per_shift} Min",
            bg=style.background,
            fg=style.foreground,
            font=("Segoe UI", 8, "bold"),
            justify="center",
            cursor="hand2",
        )
        label.bind("<Button-1>", lambda _event, shift_id=shift.id: self._select_shift(shift_id))
        return label

    def _refresh_calendar(self) -> None:
        for child in self.calendar_frame.winfo_children():
            child.destroy()
        month_start = self.week_start.replace(day=1)
        tk.Label(self.calendar_frame, text=f"{self._month_name(month_start)} {month_start.year}", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=7, sticky="w", padx=16, pady=(12, 8))
        for column, day in enumerate(self.GERMAN_WEEKDAY_ABBR):
            tk.Label(self.calendar_frame, text=day, bg="#FFFFFF", fg="#64748B", font=("Segoe UI", 8)).grid(row=1, column=column, padx=6, pady=4)
        for row_index, week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(month_start.year, month_start.month), start=2):
            for column, day in enumerate(week):
                if day == 0:
                    text, bg, fg = "", "#FFFFFF", "#94A3B8"
                else:
                    current = month_start.replace(day=day).date()
                    in_week = self.week_start.date() <= current <= (self.week_start + timedelta(days=6)).date()
                    text, bg, fg = str(day), "#DBEAFE" if in_week else "#FFFFFF", "#0B66E4" if in_week else "#475569"
                tk.Label(self.calendar_frame, text=text, bg=bg, fg=fg, width=3, pady=5).grid(row=row_index, column=column, padx=2, pady=2)

    def _refresh_absences(self) -> None:
        for child in self.absence_frame.winfo_children():
            child.destroy()
        tk.Label(self.absence_frame, text="Abwesenheiten", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        rows = [(employee, absence) for employee in self.service.employees for absence in employee.absences if self._range_in_week(absence.start, absence.end)]
        if not rows:
            tk.Label(self.absence_frame, text="Keine Abwesenheiten in dieser Woche", bg="#FFFFFF", fg="#64748B").pack(anchor="w", padx=16, pady=(0, 14))
            return
        for employee, absence in rows[:4]:
            text = f"{employee.name}\n{absence.start:%d.%m.} – {absence.end:%d.%m.}\n{absence.reason or 'Abwesenheit'}"
            label = tk.Label(self.absence_frame, text=text, bg="#FFFFFF", fg="#334155", justify="left", cursor="hand2")
            label.pack(anchor="w", padx=16, pady=(0, 12))
            label.bind("<Double-Button-1>", lambda _event, absence_id=absence.id: self._delete_absence(absence_id))

    def _refresh_details(self) -> None:
        week_shifts = self._week_shifts()
        week_shift_ids = {shift.id for shift in week_shifts}
        shift = self.service.find_shift(self.selected_shift_id) if self.selected_shift_id in week_shift_ids else None
        if shift is None and week_shifts:
            shift = week_shifts[0]
            self.selected_shift_id = shift.id
        if shift is None:
            self.selected_shift_id = None
            self.detail_title.configure(text="Schichtdetails")
            self.detail_body.configure(text="Keine Schichten in dieser Woche eingetragen.")
            return
        assigned = ", ".join(shift.employee_names) or "Nicht besetzt"
        published = f"{shift.published_at:%d.%m.%Y %H:%M} durch {shift.published_by}" if shift.published_at else "Nein"
        self.detail_title.configure(text=f"Schichtdetails · {shift.name}")
        self.detail_body.configure(
            text=(
                f"{self._weekday_name(shift.start)}, {self._format_date(shift.start)}\n"
                f"{shift.start:%H:%M} – {shift.end:%H:%M} ({shift.duration_hours:.0f} h)\n"
                f"{shift.department} – {shift.branch}\n"
                f"Kapazität: {len(shift.employee_ids)}/{shift.required_employees}\n"
                f"Zugewiesen: {assigned}\n"
                f"Veröffentlicht: {published}"
            )
        )

    def _delete_absence(self, absence_id: str) -> None:
        if not messagebox.askyesno("Abwesenheit löschen", "Soll diese Abwesenheit gelöscht werden?", parent=self):
            return
        if self.service.delete_absence(absence_id, user_id=self._current_user_id()):
            if not self._persist_changes("Abwesenheit gelöscht."):
                return
            self._refresh_all()
        else:
            self._set_status("Abwesenheit wurde nicht gefunden.")

    def _open_shift_dialog_for_selected(self) -> None:
        shift = self.service.find_shift(self.selected_shift_id) if self.selected_shift_id else None
        self._open_shift_dialog(shift)

    def _open_copy_shift_dialog_for_selected(self) -> None:
        shift = self.service.find_shift(self.selected_shift_id) if self.selected_shift_id else None
        if shift is None:
            self._set_status("Keine Schicht ausgewählt.")
            return
        self._open_copy_shift_dialog(shift)

    def _open_copy_shift_dialog(self, shift: Shift) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Schicht kopieren")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        default_start = shift.start + timedelta(days=1)
        default_end = shift.end + timedelta(days=1)
        values = {
            "source": tk.StringVar(value=f"{shift.name} · {shift.department} · {self._format_datetime(shift.start)}"),
            "start": tk.StringVar(value=self._format_datetime(default_start)),
            "end": tk.StringVar(value=self._format_datetime(default_end)),
        }
        for row, (key, label) in enumerate([("source", "Vorlage"), ("start", "Neuer Start"), ("end", "Neues Ende")]):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
            entry = ttk.Entry(dialog, textvariable=values[key], width=42)
            entry.grid(row=row, column=1, padx=18, pady=7)
            if key == "source":
                entry.configure(state="readonly")

        def copy_shift() -> None:
            try:
                start = self._parse_datetime(values["start"].get())
                end = self._parse_datetime(values["end"].get())
                copied = self.service.copy_shift(shift.id, start, end, user_id=self._current_user_id())
                self.selected_shift_id = copied.id
                if not self._persist_changes("Schicht kopiert. Mitarbeitende werden bewusst nicht übernommen.", dialog):
                    return
                dialog.destroy()
                self._refresh_all()
            except ValueError as exc:
                messagebox.showerror("Schicht kann nicht kopiert werden", str(exc), parent=dialog)

        ttk.Button(dialog, text="Kopieren", style="Primary.TButton", command=copy_shift).grid(row=3, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog

    def _open_shift_dialog(self, shift: Shift | None = None) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Schicht bearbeiten" if shift else "Schicht hinzufügen")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        values = {
            "name": tk.StringVar(value=shift.name if shift else "Frühschicht"),
            "department": tk.StringVar(value=shift.department if shift else "Kasse"),
            "start": tk.StringVar(value=self._format_datetime(shift.start if shift else self.week_start.replace(hour=6, minute=0))),
            "end": tk.StringVar(value=self._format_datetime(shift.end if shift else self.week_start.replace(hour=14, minute=0))),
            "capacity": tk.StringVar(value=str(shift.required_employees if shift else 1)),
            "qualification": tk.StringVar(value=shift.required_qualification if shift else ""),
            "branch": tk.StringVar(value=shift.branch if shift else "Hauptfiliale"),
        }
        for row, (key, label) in enumerate([("name", "Name"), ("department", "Abteilung"), ("start", "Start"), ("end", "Ende"), ("capacity", "Kapazität"), ("qualification", "Qualifikation"), ("branch", "Standort")]):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
            if key == "department":
                self._department_combobox(dialog, values[key], row)
            else:
                ttk.Entry(dialog, textvariable=values[key], width=34).grid(row=row, column=1, padx=18, pady=7)

        def save_shift() -> None:
            try:
                start = self._parse_datetime(values["start"].get())
                end = self._parse_datetime(values["end"].get())
                capacity = int(values["capacity"].get())
                if shift is None:
                    created = self.service.add_shift(values["name"].get(), values["department"].get(), start, end, capacity, values["qualification"].get(), values["branch"].get(), user_id=self._current_user_id())
                    self.selected_shift_id = created.id
                else:
                    if capacity < len(shift.employee_ids):
                        raise ValueError("Kapazität darf nicht kleiner als die aktuelle Besetzung sein.")
                    self.service.update_shift(
                        shift.id,
                        name=values["name"].get(),
                        department=values["department"].get(),
                        start=start,
                        end=end,
                        required_employees=capacity,
                        required_qualification=values["qualification"].get(),
                        branch=values["branch"].get(),
                        user_id=self._current_user_id(),
                    )
                if not self._persist_changes("Schicht gespeichert.", dialog):
                    return
                dialog.destroy()
                self._refresh_all()
            except ValueError as exc:
                messagebox.showerror("Ungültige Eingabe", str(exc), parent=dialog)

        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_shift).grid(row=7, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog

    def _open_employee_dialog(self, employee: Employee | None = None) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title("Mitarbeiter bearbeiten" if employee else "Mitarbeiter anlegen")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        values = {
            "name": tk.StringVar(value=employee.name if employee else ""),
            "department": tk.StringVar(value=employee.department if employee else "Kasse"),
            "qualification": tk.StringVar(value=employee.qualification if employee else ""),
            "hours": tk.StringVar(value=str(employee.weekly_hours_limit if employee else 40)),
            "branch": tk.StringVar(value=employee.branch if employee else "Zentrale"),
            "wage": tk.StringVar(value=str(employee.hourly_wage if employee else 15.0)),
            "break": tk.StringVar(value=str(employee.break_minutes_per_shift if employee else 30)),
            "active": tk.BooleanVar(value=employee.is_active if employee else True),
        }
        fields = [("name", "Name"), ("department", "Abteilung"), ("qualification", "Qualifikation"), ("hours", "Wochenstunden"), ("break", "Pause pro Schicht (Minuten)"), ("branch", "Filiale"), ("wage", "Stundenlohn")]
        for row, (key, label) in enumerate(fields):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
            if key == "department":
                self._department_combobox(dialog, values[key], row)
            else:
                ttk.Entry(dialog, textvariable=values[key], width=34).grid(row=row, column=1, padx=18, pady=7)
        ttk.Checkbutton(dialog, text="Aktiv", variable=values["active"]).grid(row=len(fields), column=1, sticky="w", padx=18, pady=7)

        def save_employee() -> None:
            try:
                hours = int(values["hours"].get())
                wage = float(values["wage"].get().replace(",", "."))
                break_minutes = int(values["break"].get())
                if employee is None:
                    self.service.add_employee(
                        values["name"].get(),
                        values["department"].get(),
                        values["qualification"].get(),
                        hours,
                        values["branch"].get(),
                        wage,
                        values["active"].get(),
                        break_minutes,
                        user_id=self._current_user_id(),
                    )
                else:
                    self.service.update_employee(
                        employee.id,
                        values["name"].get(),
                        values["department"].get(),
                        values["qualification"].get(),
                        hours,
                        values["branch"].get(),
                        wage,
                        values["active"].get(),
                        break_minutes,
                        user_id=self._current_user_id(),
                    )
                if not self._persist_changes("Mitarbeiter gespeichert.", dialog):
                    return
                dialog.destroy()
                self._refresh_all()
            except ValueError as exc:
                messagebox.showerror("Ungültige Eingabe", str(exc), parent=dialog)

        if employee is not None:
            def delete_employee() -> None:
                if not messagebox.askyesno("Mitarbeiter löschen", f"Soll {employee.name} wirklich gelöscht werden?", parent=dialog):
                    return
                self.service.delete_employee(employee.id, user_id=self._current_user_id())
                if not self._persist_changes("Mitarbeiter gelöscht.", dialog):
                    return
                dialog.destroy()
                self._refresh_all()

            ttk.Button(dialog, text="Löschen", style="Danger.TButton", command=delete_employee).grid(row=len(fields) + 1, column=0, sticky="w", padx=18, pady=(12, 18))
        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_employee).grid(row=len(fields) + 1, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog

    def _open_absence_dialog(self) -> tk.Toplevel | None:
        if not self.service.employees:
            messagebox.showinfo("Abwesenheit", "Bitte zuerst Mitarbeitende anlegen.", parent=self)
            return None
        dialog = tk.Toplevel(self)
        dialog.title("Abwesenheit erfassen")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        employees = sorted(self.service.employees, key=lambda item: item.name)
        employee_options = {f"{employee.name} ({employee.department})": employee.id for employee in employees}
        values = {
            "employee": tk.StringVar(value=next(iter(employee_options))),
            "start": tk.StringVar(value=self._format_datetime(self.week_start)),
            "end": tk.StringVar(value=self._format_datetime(self.week_start + timedelta(days=1))),
            "reason": tk.StringVar(value="Urlaub"),
        }
        rows = [("employee", "Mitarbeiter"), ("start", "Start"), ("end", "Ende"), ("reason", "Grund")]
        for row, (key, label) in enumerate(rows):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
            if key == "employee":
                ttk.Combobox(dialog, textvariable=values[key], values=list(employee_options), width=32, state="readonly").grid(row=row, column=1, padx=18, pady=7)
            elif key == "reason":
                ttk.Combobox(dialog, textvariable=values[key], values=DEFAULT_ABSENCE_REASONS, width=32, state="normal").grid(row=row, column=1, padx=18, pady=7)
            else:
                ttk.Entry(dialog, textvariable=values[key], width=34).grid(row=row, column=1, padx=18, pady=7)

        def save_absence() -> None:
            try:
                employee_id = employee_options[values["employee"].get()]
                self.service.add_absence(employee_id, self._parse_datetime(values["start"].get()), self._parse_datetime(values["end"].get()), values["reason"].get(), user_id=self._current_user_id())
                if not self._persist_changes("Abwesenheit gespeichert.", dialog):
                    return
                dialog.destroy()
                self._refresh_all()
            except (KeyError, ValueError) as exc:
                messagebox.showerror("Ungültige Eingabe", str(exc), parent=dialog)

        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_absence).grid(row=4, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog

    def _open_assignment_dialog(self, preselected_shift_id: str | None = None) -> tk.Toplevel | None:
        if not self.service.employees or not self.service.shifts:
            messagebox.showinfo("Zuweisung", "Bitte zuerst Mitarbeitende und Schichten anlegen.", parent=self)
            return None
        dialog = tk.Toplevel(self)
        dialog.title("Mitarbeitenden zuweisen")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        employees = sorted([item for item in self.service.employees if item.is_active], key=lambda item: item.name)
        shifts = sorted(self.service.shifts, key=lambda item: (item.start, item.name))
        employee_options = {f"{employee.name} ({employee.department}, {employee.branch})": employee.id for employee in employees}
        shift_options = {f"{shift.name} {shift.start:%d.%m. %H:%M} ({len(shift.employee_ids)}/{shift.required_employees})": shift.id for shift in shifts}
        if not employee_options:
            messagebox.showinfo("Zuweisung", "Es gibt keine aktiven Mitarbeitenden.", parent=self)
            dialog.destroy()
            return None
        selected_shift_label = next((label for label, shift_id in shift_options.items() if shift_id == preselected_shift_id), next(iter(shift_options)))
        values = {"employee": tk.StringVar(value=next(iter(employee_options))), "shift": tk.StringVar(value=selected_shift_label)}
        ignore_profile_mismatch = tk.BooleanVar(value=False)
        for row, (key, label, options) in enumerate([("employee", "Mitarbeiter", employee_options), ("shift", "Schicht", shift_options)]):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
            ttk.Combobox(dialog, textvariable=values[key], values=list(options), width=46, state="readonly").grid(row=row, column=1, padx=18, pady=7)
        ttk.Checkbutton(
            dialog,
            text="Abteilung, Filiale und Qualifikation für diese Zuweisung ignorieren",
            variable=ignore_profile_mismatch,
        ).grid(row=2, column=1, sticky="w", padx=18, pady=(4, 8))

        def assign_employee() -> None:
            try:
                result = self.service.assign(
                    employee_options[values["employee"].get()],
                    shift_options[values["shift"].get()],
                    ignore_profile_mismatch=ignore_profile_mismatch.get(),
                    user_id=self._current_user_id(),
                )
                if not result.success:
                    raise ValueError(result.message)
                if not self._persist_changes(result.message, dialog):
                    return
                dialog.destroy()
                self._refresh_all()
            except (KeyError, ValueError) as exc:
                messagebox.showerror("Zuweisung nicht möglich", str(exc), parent=dialog)

        ttk.Button(dialog, text="Zuweisen", style="Primary.TButton", command=assign_employee).grid(row=3, column=1, sticky="e", padx=18, pady=(12, 18))
        return dialog

    def _replace_shift(self, old_shift: Shift, new_shift: Shift) -> None:
        index = self.service.shifts.index(old_shift)
        self.service.shifts[index] = new_shift
        for employee in self.service.employees:
            employee.shifts = [new_shift if item.id == old_shift.id else item for item in employee.shifts]

    def _delete_selected_shift(self, parent: tk.Misc | None = None, refresh_callback: object | None = None) -> None:
        shift = self.service.find_shift(self.selected_shift_id) if self.selected_shift_id else None
        if shift is None:
            self._set_status("Keine Schicht ausgewählt.")
            return
        if not messagebox.askyesno("Schicht löschen", f"Soll '{shift.name}' wirklich gelöscht werden?", parent=parent or self):
            return
        self.service.delete_shift(shift.id, user_id=self._current_user_id())
        self.selected_shift_id = None
        self._persist_changes("Schicht gelöscht.", parent or self)
        self._refresh_all()
        if callable(refresh_callback):
            refresh_callback()

    def _select_shift(self, shift_id: str) -> None:
        self.selected_shift_id = shift_id
        self._refresh_details()

    def _move_week(self, days: int) -> None:
        self.week_start += timedelta(days=days)
        self.selected_shift_id = None
        self._refresh_all()

    def _persist_changes(self, success_message: str, parent: tk.Misc | None = None) -> bool:
        """Persist the current service state immediately after a successful edit.

        Dialog actions used to update only the in-memory service and showed
        "gespeichert" in the status bar. Persisting centrally keeps all mutation
        paths consistent and gives the user a clear error when SQLite cannot write.
        """
        try:
            self.repository.save(self.service)
        except (OSError, sqlite3.Error) as exc:
            self._set_status("Speichern fehlgeschlagen – Änderungen sind nur bis zum Beenden im Speicher.")
            messagebox.showerror("Speichern fehlgeschlagen", str(exc), parent=parent or self)
            return False
        self._set_status(success_message)
        return True

    def _save(self) -> None:
        self._persist_changes("Dienstplan gespeichert.")

    def _export_reports_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Berichte exportieren",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            output = self.service.export_reports(path, user_id=self._current_user_id())
            self._persist_changes(f"Berichte exportiert: {output}")
        except OSError as exc:
            messagebox.showerror("Export fehlgeschlagen", str(exc), parent=self)

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Dienstplan exportieren",
            defaultextension=".csv",
            filetypes=[("PDF", "*.pdf"), ("CSV", "*.csv"), ("Text", "*.txt")],
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if suffix == ".pdf":
            export_format = ExportFormat.PDF
        elif suffix == ".txt":
            export_format = ExportFormat.PDF_TEXT
        else:
            export_format = ExportFormat.CSV
        try:
            output = self.service.export_schedule(path, export_format, user_id=self._current_user_id())
            self._persist_changes(f"Exportiert: {output}")
        except OSError as exc:
            messagebox.showerror("Export fehlgeschlagen", str(exc), parent=self)

    def _import_forecast(self) -> None:
        path = filedialog.askopenfilename(title="Forecast CSV importieren", filetypes=[("CSV", "*.csv"), ("Alle Dateien", "*.*")])
        if not path:
            return
        try:
            forecasts = ForecastImportService().import_csv(path)
            added = self.service.add_forecasts(forecasts)
            if not self._persist_changes(f"{len(forecasts)} Forecast-Zeilen importiert, {added} neu gespeichert."):
                return
            self._refresh_all()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Forecast-Import fehlgeschlagen", str(exc), parent=self)

    def _publish_schedule(self) -> None:
        try:
            count = self.service.publish_week(self.week_start, user_id=self._current_user_id())
            if not self._persist_changes(f"Dienstplan veröffentlicht: {count} Schichten gespeichert."):
                return
            self._refresh_all()
        except ValueError as exc:
            messagebox.showwarning("Dienstplan prüfen", str(exc), parent=self)
        except OSError as exc:
            messagebox.showerror("Veröffentlichung fehlgeschlagen", str(exc), parent=self)

    def _apply_search(self) -> None:
        self._refresh_schedule_grid()
        self._set_status("Suche angewendet.")

    def _clear_search_placeholder(self, _event: tk.Event) -> None:
        if self.search_term.get() == "Suche nach Mitarbeitenden, Schichten...":
            self.search_term.set("")

    def _filtered_employees(self) -> list[Employee]:
        query = self.search_term.get().strip().lower()
        if not query or query == "suche nach mitarbeitenden, schichten...":
            return sorted(self.service.employees, key=lambda employee: employee.name)
        return [
            employee
            for employee in sorted(self.service.employees, key=lambda item: item.name)
            if query in employee.name.lower()
            or query in employee.department.lower()
            or query in employee.qualification.lower()
            or any(
                query in shift.name.lower() or query in shift.department.lower()
                for shift in self._employee_week_shifts(employee, self.week_start)
            )
        ]

    def _unassigned_employee_count(self) -> int:
        return sum(1 for employee in self.service.employees if self._is_unassigned_for_week(employee, self.week_start))

    def _planned_week_hours(self) -> float:
        week_shift_ids = {shift.id for shift in self._week_shifts()}
        return sum(
            employee.net_hours_for_shift(shift)
            for employee in self.service.employees
            for shift in employee.shifts
            if shift.id in week_shift_ids
        )

    @staticmethod
    def _employee_week_shifts(employee: Employee, week_start: datetime) -> list[Shift]:
        week_end = week_start + timedelta(days=7)
        return sorted(
            [shift for shift in employee.shifts if week_start <= shift.start < week_end],
            key=lambda shift: (shift.start, shift.name),
        )

    @classmethod
    def _is_unassigned_for_week(cls, employee: Employee, week_start: datetime) -> bool:
        return employee.is_active and not cls._employee_week_shifts(employee, week_start)

    @classmethod
    def _employee_week_assignment_text(cls, week_shifts: list[Shift]) -> str:
        if not week_shifts:
            return "Keine Schicht diese Woche"
        if len(week_shifts) == 1:
            shift = week_shifts[0]
            return f"{shift.name} {cls.GERMAN_WEEKDAY_ABBR[shift.start.weekday()]} {shift.start:%H:%M}"
        return f"{len(week_shifts)} Schichten diese Woche"

    def _week_shifts(self) -> list[Shift]:
        week_end = self.week_start + timedelta(days=7)
        return sorted([shift for shift in self.service.shifts if self.week_start <= shift.start < week_end], key=lambda shift: (shift.start, shift.name))

    def _week_absences(self) -> list[Absence]:
        return sorted(
            [
                absence
                for employee in self.service.employees
                for absence in employee.absences
                if self._range_in_week(absence.start, absence.end)
            ],
            key=lambda absence: (absence.start, absence.reason),
        )

    def _range_in_week(self, start: datetime, end: datetime) -> bool:
        week_end = self.week_start + timedelta(days=7)
        return start < week_end and end >= self.week_start

    @staticmethod
    def _style_for_shift(shift: Shift) -> ShiftStyle:
        normalized = shift.name.strip().lower()
        for key, style in SHIFT_STYLES.items():
            if key in normalized:
                return style
        return ShiftStyle("#E2E8F0", "#334155", shift.name)

    def _availability_text(self, employee: Employee) -> str:
        if not employee.is_active:
            return "Inaktiv"
        if employee.absences and any(self._range_in_week(absence.start, absence.end) for absence in employee.absences):
            return "Abwesend"
        if employee.planned_hours > employee.weekly_hours_limit * 0.8:
            return "Eingeschränkt"
        return "Verfügbar"

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        value = value.strip()
        for fmt in ("%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError("Datum bitte im deutschen Format 'TT.MM.JJJJ HH:MM' eingeben, zum Beispiel '01.01.2026 08:00'.")

    @staticmethod
    def _avatar(name: str) -> str:
        return "👤" if not name else "●"

    @staticmethod
    def _format_datetime(date_value: datetime) -> str:
        return date_value.strftime("%d.%m.%Y %H:%M")

    @staticmethod
    def _format_date(date_value: datetime) -> str:
        return date_value.strftime("%d.%m.%Y")

    @classmethod
    def _format_day_month(cls, date_value: datetime) -> str:
        return f"{date_value.day}. {cls.GERMAN_MONTH_ABBR[date_value.month - 1]}"

    @classmethod
    def _weekday_name(cls, date_value: datetime) -> str:
        return cls.GERMAN_WEEKDAYS[date_value.weekday()]

    @classmethod
    def _month_name(cls, date_value: datetime) -> str:
        return cls.GERMAN_MONTHS[date_value.month - 1]

    def _set_status(self, message: str) -> None:
        self.status.set(message)

    def _build_footer(self) -> None:
        footer = ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=(10, 5))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")

def create_app(
    database_path: str | Path = "python_dienstplaner/data/dienstplaner.sqlite3",
    license_path: str | Path | None = None,
) -> SchedulerApp:
    repository = SQLiteSchedulerRepository(database_path)
    service = repository.load()
    active_user_count = sum(1 for employee in service.employees if employee.is_active)
    license_result = LicenseManager(license_path).check(current_user_count=active_user_count)
    return SchedulerApp(service, repository, license_result)


def main() -> None:
    app = create_app()
    app.mainloop()


if __name__ == "__main__":
    main()
