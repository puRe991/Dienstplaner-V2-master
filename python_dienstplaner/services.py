from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List

from .exporters import ExportHeader, ExportOptions, ScheduleExporter
from .models import Absence, AssignmentResult, Employee, ExportFormat, ReportMetric, RevenueForecast, RuleProfile, Shift
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
    def __init__(self, rules: PlanningRules | None = None, rule_profiles: list[RuleProfile] | None = None) -> None:
        self.rule_profiles: list[RuleProfile] = rule_profiles or [RuleProfile()]
        self._ensure_single_active_rule_profile()
        self.rules = rules or PlanningRules(self.active_rule_profile)
        self.rules.profile = self.active_rule_profile
        self.employees: list[Employee] = []
        self.shifts: list[Shift] = []
        self.forecasts: list[RevenueForecast] = []
        self.departments: list[str] = list(DEFAULT_RETAIL_DEPARTMENTS)

    @property
    def active_rule_profile(self) -> RuleProfile:
        self._ensure_single_active_rule_profile()
        return next(profile for profile in self.rule_profiles if profile.is_active)

    def set_active_rule_profile(self, profile_id: str) -> RuleProfile:
        profile = self.find_rule_profile(profile_id)
        if profile is None:
            raise ValueError("Regelprofil wurde nicht gefunden.")
        for item in self.rule_profiles:
            item.is_active = item.id == profile.id
        self.rules.profile = profile
        return profile

    def add_rule_profile(self, profile: RuleProfile) -> RuleProfile:
        if any(item.name.lower() == profile.name.lower() for item in self.rule_profiles):
            raise ValueError("Ein Regelprofil mit diesem Namen existiert bereits.")
        if profile.is_active:
            for item in self.rule_profiles:
                item.is_active = False
        self.rule_profiles.append(profile)
        self._ensure_single_active_rule_profile()
        self.rules.profile = self.active_rule_profile
        return profile

    def update_rule_profile(self, profile_id: str, updated: RuleProfile) -> RuleProfile:
        existing = self.find_rule_profile(profile_id)
        if existing is None:
            raise ValueError("Regelprofil wurde nicht gefunden.")
        if any(item.id != profile_id and item.name.lower() == updated.name.lower() for item in self.rule_profiles):
            raise ValueError("Ein Regelprofil mit diesem Namen existiert bereits.")
        updated.id = profile_id
        index = self.rule_profiles.index(existing)
        self.rule_profiles[index] = updated
        if updated.is_active:
            for item in self.rule_profiles:
                item.is_active = item.id == profile_id
        self._ensure_single_active_rule_profile()
        self.rules.profile = self.active_rule_profile
        return updated

    def delete_rule_profile(self, profile_id: str) -> bool:
        if len(self.rule_profiles) <= 1:
            raise ValueError("Das letzte Regelprofil kann nicht gelöscht werden.")
        profile = self.find_rule_profile(profile_id)
        if profile is None:
            return False
        was_active = profile.is_active
        self.rule_profiles = [item for item in self.rule_profiles if item.id != profile_id]
        if was_active:
            self.rule_profiles[0].is_active = True
        self._ensure_single_active_rule_profile()
        self.rules.profile = self.active_rule_profile
        return True

    def find_rule_profile(self, profile_id: str) -> RuleProfile | None:
        return next((profile for profile in self.rule_profiles if profile.id == profile_id), None)

    def _ensure_single_active_rule_profile(self) -> None:
        if not self.rule_profiles:
            self.rule_profiles.append(RuleProfile())
        active_profiles = [profile for profile in self.rule_profiles if profile.is_active]
        if not active_profiles:
            self.rule_profiles[0].is_active = True
            active_profiles = [self.rule_profiles[0]]
        for profile in self.rule_profiles:
            profile.is_active = profile.id == active_profiles[0].id

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

    def export_schedule(
        self,
        path: str | Path,
        export_format: ExportFormat = ExportFormat.CSV,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        return ScheduleExporter(self.employees, self.shifts).export_schedule(path, export_format, options=options, header=header)

    def export_week_plan_pdf(
        self,
        path: str | Path,
        week_start: datetime,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        return ScheduleExporter(self.employees, self.shifts).export_week_plan_pdf(path, week_start, options=options, header=header)

    def export_day_plan_pdf(
        self,
        path: str | Path,
        day: datetime,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        return ScheduleExporter(self.employees, self.shifts).export_day_plan_pdf(path, day, options=options, header=header)

    def export_employee_plan_pdf(
        self,
        path: str | Path,
        employee_id: str,
        period_start: datetime,
        period_end: datetime,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        return ScheduleExporter(self.employees, self.shifts).export_employee_plan_pdf(
            path, employee_id, period_start, period_end, options=options, header=header
        )

    def export_reports(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["Kategorie", "Kennzahl", "Wert", "Hinweis"])
            for metric in self.create_reports():
                writer.writerow([metric.category, metric.name, metric.value, metric.note])
        return output

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


@dataclass(frozen=True)
class ImportIssue:
    """A single row-level problem found while importing a forecast CSV."""

    row_number: int
    field: str
    message: str
    severity: str = "Fehler"


@dataclass(frozen=True)
class ForecastImportReport:
    """Result of a forecast CSV import, including a per-row error report."""

    forecasts: list[RevenueForecast] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)
    total_rows: int = 0

    @property
    def imported_count(self) -> int:
        return len(self.forecasts)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "Fehler")


class ForecastImportService:
    def import_csv(self, path: str | Path) -> List[RevenueForecast]:
        report = self.import_csv_with_report(path)
        if not report.forecasts:
            raise ValueError("Forecast-Datei enthält keine gültigen Datenzeilen.")
        return report.forecasts

    def import_csv_with_report(self, path: str | Path) -> ForecastImportReport:
        input_path = Path(path)
        if not input_path.exists() or not input_path.is_file():
            raise FileNotFoundError(f"Forecast-Datei wurde nicht gefunden: {input_path}")

        forecasts: list[RevenueForecast] = []
        issues: list[ImportIssue] = []
        total_rows = 0
        with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, delimiter=";")
            header = next(reader, None)
            if header is None:
                raise ValueError("Forecast-Datei ist leer.")
            for row_number, row in enumerate(reader, start=2):
                total_rows += 1
                forecast, row_issues = self._parse_row(row, row_number)
                issues.extend(row_issues)
                if forecast is not None:
                    forecasts.append(forecast)
        return ForecastImportReport(forecasts=forecasts, issues=issues, total_rows=total_rows)

    @staticmethod
    def _parse_row(row: list[str], row_number: int) -> tuple[RevenueForecast | None, list[ImportIssue]]:
        issues: list[ImportIssue] = []
        if len(row) < 5:
            issues.append(ImportIssue(
                row_number,
                "Zeile",
                "Zeile hat zu wenige Spalten (erwartet: FilialeId;Filiale;Datum;Umsatz;Kunden).",
            ))
            return None, issues

        branch_id: int | None = None
        try:
            branch_id = int(row[0].strip())
        except (TypeError, ValueError):
            issues.append(ImportIssue(row_number, "FilialeId", f"'{row[0].strip()}' ist keine gültige Ganzzahl."))

        branch = row[1].strip()
        if not branch:
            issues.append(ImportIssue(row_number, "Filiale", "Filialname darf nicht leer sein."))

        date_value: datetime | None = None
        try:
            date_value = _parse_date(row[2])
        except ValueError as exc:
            issues.append(ImportIssue(row_number, "Datum", str(exc)))

        revenue: float | None = None
        try:
            revenue = float(row[3].replace(".", "").replace(",", "."))
        except (TypeError, ValueError):
            issues.append(ImportIssue(row_number, "Umsatz", f"'{row[3].strip()}' ist keine gültige Zahl."))

        customers: int | None = None
        try:
            customers = int(row[4].strip())
        except (TypeError, ValueError):
            issues.append(ImportIssue(row_number, "Kunden", f"'{row[4].strip()}' ist keine gültige Ganzzahl."))

        if issues:
            return None, issues
        return (
            RevenueForecast(
                branch_id=branch_id,
                branch=branch,
                date=date_value,
                expected_revenue=revenue,
                expected_customers=customers,
            ),
            issues,
        )


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
