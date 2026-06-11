from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List

from .models import Absence, AssignmentResult, Employee, ExportFormat, ReportMetric, RevenueForecast, Shift
from .rules import PlanningRules


DEFAULT_RETAIL_DEPARTMENTS: tuple[str, ...] = (
    "Kasse",
    "Verkauf / Fläche",
    "Obst & Gemüse",
    "Frische / Kühlung",
    "Backshop",
    "Getränke",
    "Drogerie",
    "Lager / Wareneingang",
    "Service / Information",
    "Marktleitung",
    "Reinigung",
    "Sicherheit",
)


class SchedulerService:
    def __init__(self, rules: PlanningRules | None = None) -> None:
        self.rules = rules or PlanningRules()
        self.employees: list[Employee] = []
        self.shifts: list[Shift] = []
        self.forecasts: list[RevenueForecast] = []
        self.departments: list[str] = list(DEFAULT_RETAIL_DEPARTMENTS)

    def add_department(self, name: str) -> str:
        department = name.strip()
        if not department:
            raise ValueError("Abteilungsname ist erforderlich.")
        if any(existing.lower() == department.lower() for existing in self.departments):
            raise ValueError("Diese Abteilung existiert bereits.")
        self.departments.append(department)
        self.departments.sort(key=str.casefold)
        return department

    def delete_department(self, name: str) -> bool:
        department = name.strip()
        if not department:
            return False
        in_use = any(item.department.lower() == department.lower() for item in [*self.employees, *self.shifts])
        if in_use:
            raise ValueError("Abteilung ist Mitarbeitenden oder Schichten zugewiesen und kann nicht gelöscht werden.")
        before = len(self.departments)
        self.departments = [item for item in self.departments if item.lower() != department.lower()]
        return len(self.departments) != before

    def department_options(self) -> list[str]:
        options = {department.strip() for department in self.departments if department.strip()}
        options.update(employee.department for employee in self.employees if employee.department.strip())
        options.update(shift.department for shift in self.shifts if shift.department.strip())
        return sorted(options, key=str.casefold)

    def add_employee(
        self,
        name: str,
        department: str,
        qualification: str = "",
        weekly_hours_limit: int = 40,
        branch: str = "Zentrale",
        hourly_wage: float = 15.0,
        is_active: bool = True,
        break_minutes_per_shift: int = 0,
    ) -> Employee:
        employee = Employee(
            name=name,
            department=department,
            qualification=qualification,
            weekly_hours_limit=weekly_hours_limit,
            branch=branch,
            hourly_wage=hourly_wage,
            is_active=is_active,
            break_minutes_per_shift=break_minutes_per_shift,
        )
        self.employees.append(employee)
        self._remember_department(employee.department)
        return employee

    def update_employee(
        self,
        employee_id: str,
        name: str,
        department: str,
        qualification: str = "",
        weekly_hours_limit: int = 40,
        branch: str = "Zentrale",
        hourly_wage: float = 15.0,
        is_active: bool = True,
        break_minutes_per_shift: int | None = None,
    ) -> Employee:
        employee = self.find_employee(employee_id)
        if employee is None:
            raise ValueError("Mitarbeiter wurde nicht gefunden.")
        updated = Employee(
            id=employee.id,
            name=name,
            department=department,
            qualification=qualification,
            weekly_hours_limit=weekly_hours_limit,
            branch=branch,
            hourly_wage=hourly_wage,
            is_active=is_active,
            break_minutes_per_shift=employee.break_minutes_per_shift if break_minutes_per_shift is None else break_minutes_per_shift,
            shifts=list(employee.shifts),
            absences=list(employee.absences),
            availabilities=list(employee.availabilities),
        )
        index = self.employees.index(employee)
        self.employees[index] = updated
        self._remember_department(updated.department)
        for shift in self.shifts:
            for pos, assigned_id in enumerate(shift.employee_ids):
                if assigned_id == updated.id and pos < len(shift.employee_names):
                    shift.employee_names[pos] = updated.name
        return updated

    def delete_employee(self, employee_id: str) -> bool:
        employee = self.find_employee(employee_id)
        if employee is None:
            return False
        self.employees = [item for item in self.employees if item.id != employee_id]
        for shift in self.shifts:
            self._remove_assignment_from_shift(shift, employee_id)
        return True

    def add_shift(
        self,
        name: str,
        department: str,
        start: datetime,
        end: datetime,
        required_employees: int,
        required_qualification: str = "",
        branch: str = "Zentrale",
    ) -> Shift:
        shift = Shift(
            name=name,
            department=department,
            start=start,
            end=end,
            required_employees=required_employees,
            required_qualification=required_qualification,
            branch=branch,
        )
        self.shifts.append(shift)
        self._remember_department(shift.department)
        return shift

    def copy_shift(self, shift_id: str, start: datetime | None = None, end: datetime | None = None) -> Shift:
        source = self.find_shift(shift_id)
        if source is None:
            raise ValueError("Schicht wurde nicht gefunden.")
        duration = source.end - source.start
        copy_start = start or source.start
        copy_end = end or (copy_start + duration)
        copied = self.add_shift(
            source.name,
            source.department,
            copy_start,
            copy_end,
            source.required_employees,
            source.required_qualification,
            source.branch,
        )
        return copied

    def assign(self, employee_id: str, shift_id: str, *, ignore_profile_mismatch: bool = False) -> AssignmentResult:
        employee = self.find_employee(employee_id)
        shift = self.find_shift(shift_id)
        outcome = self.rules.validate_assignment(employee, shift, ignore_profile_mismatch=ignore_profile_mismatch)
        if outcome.errors:
            return AssignmentResult(False, outcome.errors, outcome.warnings)

        assert employee is not None and shift is not None
        employee.shifts.append(shift)
        shift.employee_ids.append(employee.id)
        shift.employee_names.append(employee.name)
        return AssignmentResult(True, [], outcome.warnings)

    def unassign(self, employee_id: str, shift_id: str) -> bool:
        employee = self.find_employee(employee_id)
        shift = self.find_shift(shift_id)
        if employee is None or shift is None or employee_id not in shift.employee_ids:
            return False
        employee.shifts = [item for item in employee.shifts if item.id != shift_id]
        self._remove_assignment_from_shift(shift, employee_id)
        return True

    def add_absence(self, employee_id: str, start: datetime, end: datetime, reason: str = "") -> Absence:
        employee = self.find_employee(employee_id)
        if employee is None:
            raise ValueError("Mitarbeiter wurde nicht gefunden.")
        absence = Absence(start=start, end=end, reason=reason)
        conflicts = [shift for shift in employee.shifts if absence.overlaps(shift.start, shift.end)]
        if conflicts:
            names = ", ".join(f"{shift.name} {shift.start:%d.%m. %H:%M}" for shift in conflicts[:3])
            raise ValueError(f"Abwesenheit überschneidet sich mit bestehenden Schichten: {names}")
        employee.absences.append(absence)
        return absence

    def delete_absence(self, absence_id: str) -> bool:
        for employee in self.employees:
            before = len(employee.absences)
            employee.absences = [item for item in employee.absences if item.id != absence_id]
            if len(employee.absences) != before:
                return True
        return False

    def find_employee(self, employee_id: str) -> Employee | None:
        return next((employee for employee in self.employees if employee.id == employee_id), None)

    def find_shift(self, shift_id: str) -> Shift | None:
        return next((shift for shift in self.shifts if shift.id == shift_id), None)

    def publish_week(self, week_start: datetime, published_by: str = "Lokaler Modus") -> int:
        week_end = week_start + timedelta(days=7)
        week_shifts = [shift for shift in self.shifts if week_start <= shift.start < week_end]
        if not week_shifts:
            raise ValueError("In dieser Woche gibt es keine Schichten zum Veröffentlichen.")
        open_slots = sum(max(0, shift.required_employees - len(shift.employee_ids)) for shift in week_shifts)
        if open_slots:
            raise ValueError(f"Es sind noch {open_slots} offene Besetzungen vorhanden.")
        published_at = datetime.now()
        for shift in week_shifts:
            shift.published_at = published_at
            shift.published_by = published_by.strip() or "Lokaler Modus"
        return len(week_shifts)

    def add_forecasts(self, forecasts: Iterable[RevenueForecast]) -> int:
        added = 0
        existing_keys = {(item.branch_id, item.date.date()) for item in self.forecasts}
        for forecast in forecasts:
            key = (forecast.branch_id, forecast.date.date())
            if key in existing_keys:
                self.forecasts = [item for item in self.forecasts if (item.branch_id, item.date.date()) != key]
            else:
                added += 1
                existing_keys.add(key)
            self.forecasts.append(forecast)
        self.forecasts.sort(key=lambda item: (item.date, item.branch))
        return added

    def forecast_staffing_recommendations(self) -> list[ReportMetric]:
        metrics: list[ReportMetric] = []
        for forecast in self.forecasts:
            recommended = max(1, round(forecast.expected_customers / 35))
            planned = sum(shift.required_employees for shift in self.shifts if shift.branch.lower() == forecast.branch.lower() and shift.start.date() == forecast.date.date())
            delta = planned - recommended
            note = "Plan deckt Forecast" if delta >= 0 else f"{abs(delta)} Mitarbeitende zusätzlich empfohlen"
            metrics.append(ReportMetric("Forecast", f"{forecast.branch} {forecast.date:%d.%m.%Y}", f"{recommended} MA Bedarf", note))
        return metrics

    def create_reports(self) -> List[ReportMetric]:
        active_employees = [employee for employee in self.employees if employee.is_active]
        personnel_costs = sum(
            sum(employee.net_hours_for_shift(shift) * employee.hourly_wage for shift in employee.shifts)
            for employee in self.employees
        )
        occupancy = (sum(shift.occupancy_rate for shift in self.shifts) / len(self.shifts) * 100) if self.shifts else 0.0
        overtime = sum(employee.overtime for employee in self.employees)
        rule_violations = sum(1 for shift in self.shifts if len(shift.employee_ids) < shift.required_employees)
        rule_violations += sum(1 for employee in self.employees if employee.planned_hours > employee.weekly_hours_limit)

        metrics = [
            ReportMetric("Kosten", "Personalkosten", f"{personnel_costs:.2f} EUR", "Planstunden auf Basis des Stundenlohns"),
            ReportMetric("Planung", "Besetzungsgrad", f"{occupancy:.1f} %", "Zugewiesene im Verhältnis zum Bedarf"),
            ReportMetric("Personal", "Aktive Mitarbeitende", str(len(active_employees)), "Inaktive werden nicht eingeplant"),
            ReportMetric("Arbeitszeit", "Überstunden", f"{overtime:.1f} h", "Planstunden über Sollstunden"),
            ReportMetric("Compliance", "Regelverstöße", str(rule_violations), "Unterbesetzung und Limits"),
        ]
        metrics.extend(self.forecast_staffing_recommendations())
        return metrics

    def export_schedule(self, path: str | Path, export_format: ExportFormat = ExportFormat.CSV) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if export_format == ExportFormat.PDF_TEXT:
            output.write_text(self._schedule_as_text(), encoding="utf-8")
            return output

        delimiter = ";" if export_format in {ExportFormat.CSV, ExportFormat.EXCEL_COMPATIBLE} else ","
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=delimiter)
            writer.writerow(["Schicht", "Abteilung", "Filiale", "Start", "Ende", "Kapazität", "Mitarbeitende"])
            for shift in sorted(self.shifts, key=lambda item: (item.start, item.name)):
                writer.writerow([
                    shift.name,
                    shift.department,
                    shift.branch,
                    shift.start.isoformat(sep=" ", timespec="minutes"),
                    shift.end.isoformat(sep=" ", timespec="minutes"),
                    shift.required_employees,
                    ", ".join(shift.employee_names),
                ])
        return output

    def export_reports(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["Kategorie", "Kennzahl", "Wert", "Hinweis"])
            for metric in self.create_reports():
                writer.writerow([metric.category, metric.name, metric.value, metric.note])
        return output

    def _schedule_as_text(self) -> str:
        lines = ["Dienstplan", "========", ""]
        for shift in sorted(self.shifts, key=lambda item: (item.start, item.name)):
            employees = ", ".join(shift.employee_names) or "nicht besetzt"
            lines.append(f"{shift.name} | {shift.start:%d.%m.%Y %H:%M}-{shift.end:%H:%M} | {employees}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _remove_assignment_from_shift(shift: Shift, employee_id: str) -> None:
        kept_ids: list[str] = []
        kept_names: list[str] = []
        for index, assigned_id in enumerate(shift.employee_ids):
            if assigned_id == employee_id:
                continue
            kept_ids.append(assigned_id)
            kept_names.append(shift.employee_names[index] if index < len(shift.employee_names) else "")
        shift.employee_ids = kept_ids
        shift.employee_names = kept_names

    def _remember_department(self, department: str) -> None:
        normalized = department.strip()
        if normalized and not any(existing.lower() == normalized.lower() for existing in self.departments):
            self.departments.append(normalized)
            self.departments.sort(key=str.casefold)


class ForecastImportService:
    def import_csv(self, path: str | Path) -> List[RevenueForecast]:
        input_path = Path(path)
        if not input_path.exists() or not input_path.is_file():
            raise FileNotFoundError(f"Forecast-Datei wurde nicht gefunden: {input_path}")

        result: list[RevenueForecast] = []
        with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, delimiter=";")
            header = next(reader, None)
            if header is None:
                raise ValueError("Forecast-Datei ist leer.")
            for row in reader:
                forecast = self._parse_row(row)
                if forecast is not None:
                    result.append(forecast)
        if not result:
            raise ValueError("Forecast-Datei enthält keine gültigen Datenzeilen.")
        return result

    @staticmethod
    def _parse_row(row: list[str]) -> RevenueForecast | None:
        if len(row) < 5:
            return None
        try:
            revenue = float(row[3].replace(".", "").replace(",", "."))
            return RevenueForecast(
                branch_id=int(row[0]),
                branch=row[1].strip(),
                date=_parse_date(row[2]),
                expected_revenue=revenue,
                expected_customers=int(row[4]),
            )
        except (TypeError, ValueError):
            return None


def _parse_date(value: str) -> datetime:
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Ungültiges Datum: {value}")


def format_shift_options(shifts: Iterable[Shift]) -> list[str]:
    return [f"{shift.name} | {shift.start:%d.%m.%Y %H:%M} | {len(shift.employee_ids)}/{shift.required_employees}" for shift in shifts]


from .audit import install_service_audit
install_service_audit(SchedulerService)
