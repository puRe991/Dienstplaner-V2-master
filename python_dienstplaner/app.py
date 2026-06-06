from __future__ import annotations

import calendar
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .models import Absence, Employee, ExportFormat, Shift
from .repository import SQLiteSchedulerRepository
from .services import ForecastImportService, SchedulerService


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

    WEEK_START = datetime(2024, 5, 19)
    SIDEBAR_WIDTH = 250
    RIGHT_PANEL_WIDTH = 250

    def __init__(self, service: SchedulerService, repository: SQLiteSchedulerRepository) -> None:
        super().__init__()
        self.service = service
        self.repository = repository
        self.status = tk.StringVar(value="Bereit")
        self.selected_shift_id: str | None = None
        self.week_start = self.WEEK_START
        self.employee_rows: dict[str, int] = {}
        self.schedule_cells: dict[tuple[str, int], tk.Label] = {}

        self.title("Dienstplanung Pro")
        self.geometry("1440x840")
        self.minsize(1180, 720)
        self.configure(bg="#F8FAFC")
        self._configure_styles()
        self._ensure_demo_data()
        self._build_ui()
        self._refresh_all()

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

        tk.Label(header, text="🔔 3", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 12)).grid(row=0, column=3, padx=(12, 24))
        tk.Label(header, text="Max Mustermann\nAdministrator", bg="#FFFFFF", fg="#0F172A", justify="left", font=("Segoe UI", 10)).grid(row=0, column=4, padx=(0, 24))

    def _build_sidebar(self) -> None:
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=self.SIDEBAR_WIDTH)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        for index, item in enumerate(["⌂  Dashboard", "▣  Dienstplan", "👥  Mitarbeiter", "☂  Abwesenheiten", "◷  Schichten", "▥  Berichte", "⚙  Einstellungen"]):
            style = "SidebarActive.TLabel" if "Dienstplan" in item else "Sidebar.TLabel"
            label = ttk.Label(sidebar, text=item, style=style, padding=(24, 14))
            label.grid(row=index, column=0, sticky="ew", padx=14, pady=(8 if index == 0 else 0, 0))

        sidebar.rowconfigure(8, weight=1)
        card = tk.Frame(sidebar, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        card.grid(row=9, column=0, sticky="ew", padx=20, pady=20)
        tk.Label(card, text="🌙  Nächste Schicht", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(16, 12))
        tk.Label(card, text="Heute, 20:00 – 06:00", bg="#FFFFFF", fg="#0F172A").pack(anchor="w", padx=18)
        tk.Label(card, text="Nachtschicht", bg="#DBEAFE", fg="#0B4DB3", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=8)
        tk.Label(card, text="Standort\n📍  Zentrale Wache", bg="#FFFFFF", fg="#475569", justify="left").pack(anchor="w", padx=18, pady=(16, 18))
        tk.Label(sidebar, text="© 2024 Dienstplanung Pro", bg="#FFFFFF", fg="#64748B").grid(row=10, column=0, sticky="w", padx=24, pady=(0, 16))

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
        ttk.Button(toolbar, text="Ansicht", style="Ghost.TButton", command=self._show_view_info).grid(row=0, column=4, padx=6)
        ttk.Button(toolbar, text="+ Schicht hinzufügen", style="Primary.TButton", command=self._open_shift_dialog).grid(row=0, column=5, padx=6)

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
        self.grid_frame = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        self.grid_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_frame.columnconfigure(0, minsize=160)
        for column in range(1, 8):
            self.grid_frame.columnconfigure(column, weight=1, minsize=115)

    def _build_legend_and_details(self, parent: ttk.Frame) -> None:
        legend = ttk.Frame(parent)
        legend.grid(row=1, column=0, sticky="ew", pady=(14, 10))
        items = [
            ("#A7E8B0", "Frühschicht\n06:00 – 14:00"),
            ("#F8C266", "Spätschicht\n14:00 – 22:00"),
            ("#7BAAF7", "Nachtschicht\n22:00 – 06:00"),
            ("#C084FC", "Bereitschaft\n24h"),
            ("#F87171", "Abwesend\n–"),
            ("#CBD5E1", "Offene Schicht\nNicht besetzt"),
        ]
        for color, label in items:
            item = ttk.Frame(legend)
            item.pack(side="left", padx=(0, 28))
            tk.Label(item, text="●", fg=color, bg="#F8FAFC", font=("Segoe UI", 14)).pack(side="left")
            ttk.Label(item, text=label, style="Muted.TLabel", justify="left").pack(side="left", padx=(6, 0))

        details = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        details.grid(row=2, column=0, sticky="ew")
        details.columnconfigure(1, weight=1)
        self.detail_title = tk.Label(details, text="Schichtdetails", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 11, "bold"))
        self.detail_title.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))
        self.detail_body = tk.Label(details, text="Bitte eine Schicht auswählen.", bg="#FFFFFF", fg="#334155", justify="left")
        self.detail_body.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))
        ttk.Button(details, text="Bearbeiten", style="Ghost.TButton", command=self._open_shift_dialog_for_selected).grid(row=1, column=2, padx=4, pady=14)
        ttk.Button(details, text="Tauschanfrage", style="Ghost.TButton", command=self._show_swap_info).grid(row=1, column=3, padx=4, pady=14)
        ttk.Button(details, text="Löschen", style="Danger.TButton", command=self._delete_selected_shift).grid(row=1, column=4, padx=(4, 18), pady=14)

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
            ("↔  Tauschanfrage erstellen", self._show_swap_info),
            ("▤  Schichtvorlage anlegen", self._open_shift_dialog),
            ("✈  Dienstplan veröffentlichen", self._publish_schedule),
            ("📈 Forecast importieren", self._import_forecast),
        ]:
            ttk.Button(actions, text=text, style="Ghost.TButton", command=command).pack(fill="x", padx=12, pady=5)
        ttk.Button(actions, text="💾 Speichern", style="Ghost.TButton", command=self._save).pack(fill="x", padx=12, pady=(5, 12))
        ttk.Button(actions, text="CSV Export", style="Ghost.TButton", command=self._export_csv).pack(fill="x", padx=12, pady=(0, 12))

    def _refresh_all(self) -> None:
        self.week_label.configure(text=f"📅  {self.week_start.day}. – {(self.week_start + timedelta(days=6)).day}. {self._month_name(self.week_start)} {self.week_start.year}")
        self._refresh_cards()
        self._refresh_schedule_grid()
        self._refresh_calendar()
        self._refresh_absences()
        self._refresh_details()

    def _refresh_cards(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()
        open_shifts = sum(max(0, shift.required_employees - len(shift.employee_ids)) for shift in self._week_shifts())
        absences = sum(1 for employee in self.service.employees for absence in employee.absences if self._range_in_week(absence.start, absence.end))
        hours = sum(shift.duration_hours * len(shift.employee_ids) for shift in self._week_shifts())
        avg_hours = hours / max(1, len(self.service.employees))
        cards = [
            ("👥", "Mitarbeiter", str(len(self.service.employees)), "Aktiv"),
            ("▣", "Offene Schichten", str(open_shifts), "Davon 2 kritisch" if open_shifts else "Voll besetzt"),
            ("☂", "Abwesenheiten", str(absences), "Genehmigt"),
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
            text = header if column == 0 else f"{header}\n{(self.week_start + timedelta(days=column - 1)):%d. %b}"
            tk.Label(self.grid_frame, text=text, bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 9, "bold"), justify="center", height=3).grid(row=0, column=column, sticky="nsew")

        filtered_employees = self._filtered_employees()
        for row_index, employee in enumerate(filtered_employees, start=1):
            self.employee_rows[employee.id] = row_index
            employee_text = f"{self._avatar(employee.name)}  {employee.name}\n{employee.qualification or employee.department}\n● {self._availability_text(employee)}"
            tk.Label(self.grid_frame, text=employee_text, bg="#FFFFFF", fg="#0F172A", justify="left", anchor="w", padx=14, pady=8).grid(row=row_index, column=0, sticky="nsew")
            for day_index in range(7):
                cell = self._make_schedule_cell(employee, day_index)
                cell.grid(row=row_index, column=day_index + 1, sticky="nsew", padx=4, pady=5)
                self.schedule_cells[(employee.id, day_index)] = cell

    def _make_schedule_cell(self, employee: Employee, day_index: int) -> tk.Label:
        day = self.week_start.date() + timedelta(days=day_index)
        absence = next((item for item in employee.absences if item.start.date() <= day <= item.end.date()), None)
        if absence is not None:
            return tk.Label(self.grid_frame, text=f"Abwesend\n{absence.reason or 'Abwesenheit'}", bg="#FEE2E2", fg="#DC2626", font=("Segoe UI", 8, "bold"), justify="center")

        shift = next((item for item in employee.shifts if item.start.date() == day), None)
        if shift is None:
            return tk.Label(self.grid_frame, text="-", bg="#FFFFFF", fg="#64748B", font=("Segoe UI", 12, "bold"))
        style = self._style_for_shift(shift)
        label = tk.Label(self.grid_frame, text=f"{shift.start:%H:%M} – {shift.end:%H:%M}\n{style.label}", bg=style.background, fg=style.foreground, font=("Segoe UI", 8, "bold"), justify="center", cursor="hand2")
        label.bind("<Button-1>", lambda _event, shift_id=shift.id: self._select_shift(shift_id))
        return label

    def _refresh_calendar(self) -> None:
        for child in self.calendar_frame.winfo_children():
            child.destroy()
        month_start = self.week_start.replace(day=1)
        tk.Label(self.calendar_frame, text=f"{self._month_name(month_start)} {month_start.year}", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=7, sticky="w", padx=16, pady=(12, 8))
        for column, day in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
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
            tk.Label(self.absence_frame, text=text, bg="#FFFFFF", fg="#334155", justify="left").pack(anchor="w", padx=16, pady=(0, 12))

    def _refresh_details(self) -> None:
        shift = self.service.find_shift(self.selected_shift_id) if self.selected_shift_id else None
        if shift is None and self.service.shifts:
            shift = self._week_shifts()[0] if self._week_shifts() else self.service.shifts[0]
            self.selected_shift_id = shift.id
        if shift is None:
            self.detail_title.configure(text="Schichtdetails")
            self.detail_body.configure(text="Keine Schichten vorhanden.")
            return
        assigned = ", ".join(shift.employee_names) or "Nicht besetzt"
        self.detail_title.configure(text=f"Schichtdetails · {shift.name}")
        self.detail_body.configure(
            text=(
                f"{shift.start:%A, %d.%m.%Y}\n"
                f"{shift.start:%H:%M} – {shift.end:%H:%M} ({shift.duration_hours:.0f} h)\n"
                f"Station 1 – {shift.branch}\n"
                f"Zugewiesen: {assigned}"
            )
        )

    def _open_shift_dialog_for_selected(self) -> None:
        shift = self.service.find_shift(self.selected_shift_id) if self.selected_shift_id else None
        self._open_shift_dialog(shift)

    def _open_shift_dialog(self, shift: Shift | None = None) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Schicht bearbeiten" if shift else "Schicht hinzufügen")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg="#FFFFFF")
        values = {
            "name": tk.StringVar(value=shift.name if shift else "Frühschicht"),
            "department": tk.StringVar(value=shift.department if shift else "Pflege"),
            "start": tk.StringVar(value=(shift.start if shift else self.week_start.replace(hour=6, minute=0)).strftime("%Y-%m-%d %H:%M")),
            "end": tk.StringVar(value=(shift.end if shift else self.week_start.replace(hour=14, minute=0)).strftime("%Y-%m-%d %H:%M")),
            "capacity": tk.StringVar(value=str(shift.required_employees if shift else 1)),
            "qualification": tk.StringVar(value=shift.required_qualification if shift else "Pflegefachkraft"),
            "branch": tk.StringVar(value=shift.branch if shift else "Zentrale Wache"),
        }
        for row, (key, label) in enumerate([("name", "Name"), ("department", "Abteilung"), ("start", "Start"), ("end", "Ende"), ("capacity", "Kapazität"), ("qualification", "Qualifikation"), ("branch", "Standort")]):
            tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
            ttk.Entry(dialog, textvariable=values[key], width=34).grid(row=row, column=1, padx=18, pady=7)

        def save_shift() -> None:
            try:
                start = self._parse_datetime(values["start"].get())
                end = self._parse_datetime(values["end"].get())
                capacity = int(values["capacity"].get())
                if shift is None:
                    created = self.service.add_shift(values["name"].get(), values["department"].get(), start, end, capacity, values["qualification"].get(), values["branch"].get())
                    self.selected_shift_id = created.id
                else:
                    if capacity < len(shift.employee_ids):
                        raise ValueError("Kapazität darf nicht kleiner als die aktuelle Besetzung sein.")
                    updated = Shift(
                        id=shift.id,
                        employee_ids=list(shift.employee_ids),
                        employee_names=list(shift.employee_names),
                        name=values["name"].get(),
                        department=values["department"].get(),
                        start=start,
                        end=end,
                        required_employees=capacity,
                        required_qualification=values["qualification"].get(),
                        branch=values["branch"].get(),
                    )
                    self._replace_shift(shift, updated)
                dialog.destroy()
                self._refresh_all()
                self._set_status("Schicht gespeichert.")
            except ValueError as exc:
                messagebox.showerror("Ungültige Eingabe", str(exc), parent=dialog)

        ttk.Button(dialog, text="Speichern", style="Primary.TButton", command=save_shift).grid(row=7, column=1, sticky="e", padx=18, pady=(12, 18))

    def _replace_shift(self, old_shift: Shift, new_shift: Shift) -> None:
        index = self.service.shifts.index(old_shift)
        self.service.shifts[index] = new_shift
        for employee in self.service.employees:
            employee.shifts = [new_shift if item.id == old_shift.id else item for item in employee.shifts]

    def _delete_selected_shift(self) -> None:
        shift = self.service.find_shift(self.selected_shift_id) if self.selected_shift_id else None
        if shift is None:
            self._set_status("Keine Schicht ausgewählt.")
            return
        if not messagebox.askyesno("Schicht löschen", f"Soll '{shift.name}' wirklich gelöscht werden?", parent=self):
            return
        self.service.shifts = [item for item in self.service.shifts if item.id != shift.id]
        for employee in self.service.employees:
            employee.shifts = [item for item in employee.shifts if item.id != shift.id]
        self.selected_shift_id = None
        self._refresh_all()
        self._set_status("Schicht gelöscht.")

    def _select_shift(self, shift_id: str) -> None:
        self.selected_shift_id = shift_id
        self._refresh_details()

    def _move_week(self, days: int) -> None:
        self.week_start += timedelta(days=days)
        self.selected_shift_id = None
        self._refresh_all()

    def _save(self) -> None:
        try:
            self.repository.save(self.service)
            self._set_status("Dienstplan gespeichert.")
        except OSError as exc:
            messagebox.showerror("Speichern fehlgeschlagen", str(exc), parent=self)

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Dienstplan exportieren",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Text", "*.txt")],
        )
        if not path:
            return
        export_format = ExportFormat.PDF_TEXT if Path(path).suffix.lower() == ".txt" else ExportFormat.CSV
        try:
            output = self.service.export_schedule(path, export_format)
            self._set_status(f"Exportiert: {output}")
        except OSError as exc:
            messagebox.showerror("Export fehlgeschlagen", str(exc), parent=self)

    def _import_forecast(self) -> None:
        path = filedialog.askopenfilename(title="Forecast CSV importieren", filetypes=[("CSV", "*.csv"), ("Alle Dateien", "*.*")])
        if not path:
            return
        forecasts = ForecastImportService().import_csv(path)
        self._set_status(f"{len(forecasts)} Forecast-Zeilen importiert.")

    def _publish_schedule(self) -> None:
        open_slots = sum(max(0, shift.required_employees - len(shift.employee_ids)) for shift in self._week_shifts())
        if open_slots:
            messagebox.showwarning("Dienstplan prüfen", f"Es sind noch {open_slots} offene Besetzungen vorhanden.", parent=self)
            return
        self._set_status("Dienstplan veröffentlicht.")

    def _show_view_info(self) -> None:
        messagebox.showinfo("Ansicht", "Die Python-Version zeigt aktuell die Wochenansicht.", parent=self)

    def _show_swap_info(self) -> None:
        messagebox.showinfo("Tauschanfrage", "Tauschanfragen sind vorbereitet und werden als Schnellaktion protokolliert.", parent=self)
        self._set_status("Tauschanfrage vorbereitet.")

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
        return [employee for employee in sorted(self.service.employees, key=lambda item: item.name) if query in employee.name.lower() or query in employee.department.lower() or query in employee.qualification.lower()]

    def _week_shifts(self) -> list[Shift]:
        week_end = self.week_start + timedelta(days=7)
        return sorted([shift for shift in self.service.shifts if self.week_start <= shift.start < week_end], key=lambda shift: (shift.start, shift.name))

    def _range_in_week(self, start: datetime, end: datetime) -> bool:
        week_end = self.week_start + timedelta(days=7)
        return start < week_end and end >= self.week_start

    def _style_for_shift(self, shift: Shift) -> ShiftStyle:
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
        for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError("Datum bitte als 'YYYY-MM-DD HH:MM' oder 'DD.MM.YYYY HH:MM' eingeben.")

    @staticmethod
    def _avatar(name: str) -> str:
        return "👤" if not name else "●"

    @staticmethod
    def _month_name(date_value: datetime) -> str:
        names = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        return names[date_value.month - 1]

    def _set_status(self, message: str) -> None:
        self.status.set(message)

    def _build_footer(self) -> None:
        footer = ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=(10, 5))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")

    def _ensure_demo_data(self) -> None:
        if self.service.employees or self.service.shifts:
            return
        employees = [
            self.service.add_employee("Anna Berger", "Pflege", "Pflegefachkraft", 48, "Zentrale Wache", 23.5),
            self.service.add_employee("Lukas Hofmann", "Pflege", "Pflegefachkraft", 40, "Zentrale Wache", 22.0),
            self.service.add_employee("Julia Schneider", "Pflege", "Altenpflegerin", 40, "Zentrale Wache", 21.0),
            self.service.add_employee("Markus Weber", "Pflege", "Pflegehelfer", 30, "Zentrale Wache", 18.5),
            self.service.add_employee("Sarah Müller", "Pflege", "Pflegefachkraft", 35, "Zentrale Wache", 23.0),
            self.service.add_employee("Thomas Richter", "Pflege", "Pflegehelfer", 32, "Zentrale Wache", 18.0),
            self.service.add_employee("Lisa Wagner", "Pflege", "Pflegefachkraft", 40, "Zentrale Wache", 23.5),
        ]
        employees[-1].absences.append(Absence(self.week_start, self.week_start + timedelta(days=6, hours=23), "Urlaub"))
        patterns = {
            0: ["Frühschicht", "Frühschicht", "Frühschicht", "Frühschicht", None, "Spätschicht", "Spätschicht"],
            1: ["Spätschicht", "Spätschicht", None, "Spätschicht", "Spätschicht", None, None],
            2: ["Nachtschicht", "Nachtschicht", None, "Nachtschicht", "Nachtschicht", None, "Nachtschicht"],
            3: [None, "Frühschicht", None, "Frühschicht", None, "Frühschicht", None],
            4: ["Spätschicht", None, "Spätschicht", None, "Spätschicht", "Spätschicht", None],
            5: [None, "Nachtschicht", "Nachtschicht", None, "Nachtschicht", None, "Nachtschicht"],
        }
        shift_times = {
            "Frühschicht": (time(6, 0), time(14, 0)),
            "Spätschicht": (time(14, 0), time(22, 0)),
            "Nachtschicht": (time(22, 0), time(6, 0)),
        }
        for employee_index, daily_names in patterns.items():
            employee = employees[employee_index]
            for day_index, shift_name in enumerate(daily_names):
                if shift_name is None:
                    continue
                start_time, end_time = shift_times[shift_name]
                day = self.week_start + timedelta(days=day_index)
                start = datetime.combine(day.date(), start_time)
                end_date = day.date() + (timedelta(days=1) if end_time <= start_time else timedelta())
                end = datetime.combine(end_date, end_time)
                shift = self.service.add_shift(shift_name, employee.department, start, end, 1, employee.qualification, employee.branch)
                result = self.service.assign(employee.id, shift.id)
                if not result.success:
                    raise RuntimeError(result.message)


def create_app(database_path: str | Path = "python_dienstplaner/data/dienstplaner.sqlite3") -> SchedulerApp:
    repository = SQLiteSchedulerRepository(database_path)
    service = repository.load()
    return SchedulerApp(service, repository)


def main() -> None:
    app = create_app()
    app.mainloop()


if __name__ == "__main__":
    main()
