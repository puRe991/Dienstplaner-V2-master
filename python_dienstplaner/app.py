from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .models import ExportFormat
from .repository import SQLiteSchedulerRepository
from .services import ForecastImportService, SchedulerService


class SchedulerApp(tk.Tk):
    def __init__(self, service: SchedulerService, repository: SQLiteSchedulerRepository) -> None:
        super().__init__()
        self.title("Dienstplaner Python")
        self.geometry("1100x720")
        self.minsize(960, 620)
        self.service = service
        self.repository = repository
        self.status = tk.StringVar(value="Bereit")
        self._build_ui()
        self._refresh_all()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(16, 12))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Dienstplaner Python", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Speichern", command=self._save).grid(row=0, column=1, padx=4)
        ttk.Button(header, text="CSV Export", command=self._export_csv).grid(row=0, column=2, padx=4)
        ttk.Button(header, text="Forecast importieren", command=self._import_forecast).grid(row=0, column=3, padx=4)

        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self.plan_tab = ttk.Frame(notebook, padding=12)
        self.report_tab = ttk.Frame(notebook, padding=12)
        notebook.add(self.plan_tab, text="Dienstplan")
        notebook.add(self.report_tab, text="Reports")
        self._build_plan_tab()
        self._build_report_tab()

        footer = ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=(8, 4))
        footer.grid(row=2, column=0, sticky="ew")

    def _build_plan_tab(self) -> None:
        self.plan_tab.columnconfigure(0, weight=1)
        self.plan_tab.columnconfigure(1, weight=1)
        self.plan_tab.rowconfigure(1, weight=1)

        employee_form = ttk.LabelFrame(self.plan_tab, text="Mitarbeiter anlegen", padding=10)
        employee_form.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        self.employee_name = tk.StringVar()
        self.employee_department = tk.StringVar(value="Kasse")
        self.employee_qualification = tk.StringVar(value="Kasse")
        self.employee_hours = tk.IntVar(value=40)
        self._entry(employee_form, "Name", self.employee_name, 0)
        self._entry(employee_form, "Abteilung", self.employee_department, 1)
        self._entry(employee_form, "Qualifikation", self.employee_qualification, 2)
        self._entry(employee_form, "Wochenstunden", self.employee_hours, 3)
        ttk.Button(employee_form, text="Hinzufügen", command=self._add_employee).grid(row=4, column=1, sticky="e", pady=(8, 0))

        shift_form = ttk.LabelFrame(self.plan_tab, text="Schicht anlegen", padding=10)
        shift_form.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.shift_name = tk.StringVar(value="Frühschicht")
        self.shift_department = tk.StringVar(value="Kasse")
        self.shift_start = tk.StringVar(value=(datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"))
        self.shift_end = tk.StringVar(value=(datetime.now().replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"))
        self.shift_capacity = tk.IntVar(value=2)
        self.shift_qualification = tk.StringVar(value="Kasse")
        self._entry(shift_form, "Name", self.shift_name, 0)
        self._entry(shift_form, "Abteilung", self.shift_department, 1)
        self._entry(shift_form, "Start", self.shift_start, 2)
        self._entry(shift_form, "Ende", self.shift_end, 3)
        self._entry(shift_form, "Kapazität", self.shift_capacity, 4)
        self._entry(shift_form, "Qualifikation", self.shift_qualification, 5)
        ttk.Button(shift_form, text="Hinzufügen", command=self._add_shift).grid(row=6, column=1, sticky="e", pady=(8, 0))

        lists = ttk.Frame(self.plan_tab)
        lists.grid(row=1, column=0, columnspan=2, sticky="nsew")
        lists.columnconfigure(0, weight=1)
        lists.columnconfigure(1, weight=1)
        lists.rowconfigure(0, weight=1)

        employee_box = ttk.LabelFrame(lists, text="Mitarbeitende", padding=8)
        employee_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        employee_box.rowconfigure(0, weight=1)
        employee_box.columnconfigure(0, weight=1)
        self.employee_list = tk.Listbox(employee_box, height=12)
        self.employee_list.grid(row=0, column=0, sticky="nsew")

        shift_box = ttk.LabelFrame(lists, text="Schichten", padding=8)
        shift_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        shift_box.rowconfigure(0, weight=1)
        shift_box.columnconfigure(0, weight=1)
        self.shift_list = tk.Listbox(shift_box, height=12)
        self.shift_list.grid(row=0, column=0, sticky="nsew")
        ttk.Button(shift_box, text="Ausgewählten Mitarbeiter zuweisen", command=self._assign_selected).grid(row=1, column=0, sticky="e", pady=(8, 0))

    def _build_report_tab(self) -> None:
        self.report_tab.columnconfigure(0, weight=1)
        self.report_tab.rowconfigure(0, weight=1)
        columns = ("category", "name", "value", "note")
        self.report_tree = ttk.Treeview(self.report_tab, columns=columns, show="headings")
        for column, label in zip(columns, ("Kategorie", "Name", "Wert", "Hinweis")):
            self.report_tree.heading(column, text=label)
            self.report_tree.column(column, width=180 if column != "note" else 360)
        self.report_tree.grid(row=0, column=0, sticky="nsew")
        ttk.Button(self.report_tab, text="Aktualisieren", command=self._refresh_reports).grid(row=1, column=0, sticky="e", pady=(8, 0))

    @staticmethod
    def _entry(parent: ttk.Frame, label: str, variable: tk.Variable, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=2)
        parent.columnconfigure(1, weight=1)

    def _add_employee(self) -> None:
        try:
            self.service.add_employee(
                self.employee_name.get(),
                self.employee_department.get(),
                self.employee_qualification.get(),
                int(self.employee_hours.get()),
            )
            self.employee_name.set("")
            self.status.set("Mitarbeiter hinzugefügt")
            self._refresh_all()
        except (TypeError, ValueError) as exc:
            self._show_error(str(exc))

    def _add_shift(self) -> None:
        try:
            self.service.add_shift(
                self.shift_name.get(),
                self.shift_department.get(),
                datetime.strptime(self.shift_start.get().strip(), "%Y-%m-%d %H:%M"),
                datetime.strptime(self.shift_end.get().strip(), "%Y-%m-%d %H:%M"),
                int(self.shift_capacity.get()),
                self.shift_qualification.get(),
            )
            self.status.set("Schicht hinzugefügt")
            self._refresh_all()
        except (TypeError, ValueError) as exc:
            self._show_error(str(exc))

    def _assign_selected(self) -> None:
        employee_index = self._selected_index(self.employee_list)
        shift_index = self._selected_index(self.shift_list)
        if employee_index is None or shift_index is None:
            self._show_error("Bitte Mitarbeiter und Schicht auswählen.")
            return
        result = self.service.assign(self.service.employees[employee_index].id, self.service.shifts[shift_index].id)
        if not result.success:
            self._show_error(result.message)
            return
        self.status.set(result.message)
        self._refresh_all()

    @staticmethod
    def _selected_index(listbox: tk.Listbox) -> int | None:
        selection = listbox.curselection()
        return int(selection[0]) if selection else None

    def _save(self) -> None:
        try:
            self.repository.save(self.service)
            self.status.set("Daten gespeichert")
        except OSError as exc:
            self._show_error(f"Speichern fehlgeschlagen: {exc}")

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            self.service.export_schedule(path, ExportFormat.CSV)
            self.status.set(f"Export erstellt: {path}")
        except OSError as exc:
            self._show_error(f"Export fehlgeschlagen: {exc}")

    def _import_forecast(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Alle Dateien", "*.*")])
        if not path:
            return
        forecasts = ForecastImportService().import_csv(path)
        self.status.set(f"{len(forecasts)} Forecast-Zeilen importiert")

    def _refresh_all(self) -> None:
        self._refresh_employees()
        self._refresh_shifts()
        self._refresh_reports()

    def _refresh_employees(self) -> None:
        self.employee_list.delete(0, tk.END)
        for employee in self.service.employees:
            self.employee_list.insert(tk.END, f"{employee.name} | {employee.department} | {employee.planned_hours:.1f}/{employee.weekly_hours_limit} h")

    def _refresh_shifts(self) -> None:
        self.shift_list.delete(0, tk.END)
        for shift in self.service.shifts:
            employees = ", ".join(shift.employee_names) or "offen"
            self.shift_list.insert(tk.END, f"{shift.name} | {shift.start:%d.%m.%Y %H:%M} | {len(shift.employee_ids)}/{shift.required_employees} | {employees}")

    def _refresh_reports(self) -> None:
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        for metric in self.service.create_reports():
            self.report_tree.insert("", tk.END, values=(metric.category, metric.name, metric.value, metric.note))

    def _show_error(self, message: str) -> None:
        safe_message = message or "Unbekannter Fehler"
        self.status.set(safe_message)
        messagebox.showerror("Dienstplaner", safe_message)


def create_app(database_path: str | Path = "python_dienstplaner/data/dienstplaner.sqlite3") -> SchedulerApp:
    repository = SQLiteSchedulerRepository(database_path)
    service = repository.load()
    if not service.employees and not service.shifts:
        _seed_demo_data(service)
    return SchedulerApp(service, repository)


def _seed_demo_data(service: SchedulerService) -> None:
    service.add_employee("Max Muster", "Kasse", "Kasse", 40)
    service.add_employee("Eva Retail", "Lager", "Lager", 35)
    tomorrow = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
    service.add_shift("Kasse Früh", "Kasse", tomorrow, tomorrow + timedelta(hours=8), 2, "Kasse")
    service.add_shift("Lager Spät", "Lager", tomorrow.replace(hour=14), tomorrow.replace(hour=22), 1, "Lager")


def main() -> None:
    app = create_app()
    app.mainloop()
