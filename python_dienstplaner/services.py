from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .models import AssignmentResult, Employee, ExportFormat, ReportMetric, RevenueForecast, Shift
from .rules import PlanningRules


class SchedulerService:
    def __init__(self, rules: PlanningRules | None = None) -> None:
        self.rules = rules or PlanningRules()
        self.employees: list[Employee] = []
        self.shifts: list[Shift] = []

    def add_employee(
        self,
        name: str,
        department: str,
        qualification: str = "",
        weekly_hours_limit: int = 40,
        branch: str = "Zentrale",
        hourly_wage: float = 15.0,
    ) -> Employee:
        employee = Employee(
            name=name,
            department=department,
            qualification=qualification,
            weekly_hours_limit=weekly_hours_limit,
            branch=branch,
            hourly_wage=hourly_wage,
        )
        self.employees.append(employee)
        return employee

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
        return shift

    def assign(self, employee_id: str, shift_id: str) -> AssignmentResult:
        employee = self.find_employee(employee_id)
        shift = self.find_shift(shift_id)
        outcome = self.rules.validate_assignment(employee, shift)
        if outcome.errors:
            return AssignmentResult(False, outcome.errors, outcome.warnings)

        assert employee is not None and shift is not None
        employee.shifts.append(shift)
        shift.employee_ids.append(employee.id)
        shift.employee_names.append(employee.name)
        return AssignmentResult(True, [], outcome.warnings)

    def find_employee(self, employee_id: str) -> Employee | None:
        return next((employee for employee in self.employees if employee.id == employee_id), None)

    def find_shift(self, shift_id: str) -> Shift | None:
        return next((shift for shift in self.shifts if shift.id == shift_id), None)

    def create_reports(self) -> List[ReportMetric]:
        personnel_costs = sum(
            sum(shift.duration_hours * employee.hourly_wage for shift in employee.shifts)
            for employee in self.employees
        )
        occupancy = (sum(shift.occupancy_rate for shift in self.shifts) / len(self.shifts) * 100) if self.shifts else 0.0
        overtime = sum(employee.overtime for employee in self.employees)
        rule_violations = sum(1 for shift in self.shifts if len(shift.employee_ids) < shift.required_employees)
        rule_violations += sum(1 for employee in self.employees if employee.planned_hours > employee.weekly_hours_limit)

        return [
            ReportMetric("Kosten", "Personalkosten", f"{personnel_costs:.2f} EUR", "Iststunden auf Basis des Stundenlohns"),
            ReportMetric("Planung", "Besetzungsgrad", f"{occupancy:.1f} %", "Zugewiesene im Verhältnis zum Bedarf"),
            ReportMetric("Arbeitszeit", "Überstunden", f"{overtime:.1f} h", "Iststunden über Sollstunden"),
            ReportMetric("Compliance", "Regelverstöße", str(rule_violations), "Unterbesetzung und Limits"),
        ]

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
            for shift in self.shifts:
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

    def _schedule_as_text(self) -> str:
        lines = ["Dienstplan", "========", ""]
        for shift in self.shifts:
            employees = ", ".join(shift.employee_names) or "nicht besetzt"
            lines.append(f"{shift.name} | {shift.start:%d.%m.%Y %H:%M}-{shift.end:%H:%M} | {employees}")
        return "\n".join(lines) + "\n"


class ForecastImportService:
    def import_csv(self, path: str | Path) -> List[RevenueForecast]:
        input_path = Path(path)
        if not input_path.exists() or not input_path.is_file():
            return []

        result: list[RevenueForecast] = []
        with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, delimiter=";")
            next(reader, None)
            for row in reader:
                forecast = self._parse_row(row)
                if forecast is not None:
                    result.append(forecast)
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
