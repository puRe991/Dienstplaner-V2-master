from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List
from uuid import uuid4


class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL_COMPATIBLE = "excel"
    PDF_TEXT = "pdf_text"
    PDF = "pdf"


DEFAULT_ABSENCE_REASONS: tuple[str, ...] = (
    "Urlaub",
    "Freier Tag",
    "Krank",
    "Fortbildung",
    "Seminar",
    "Berufsschule",
    "Sonderurlaub",
    "Unbezahlt frei",
    "Elternzeit",
    "Pflegezeit",
    "Behördengang",
    "Sonstige Abwesenheit",
)


@dataclass(frozen=True)
class LicenseInfo:
    company_name: str
    license_id: str
    valid_until: date
    max_users: int
    features: List[str]
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.company_name.strip():
            raise ValueError("Firmenname ist erforderlich.")
        if not self.license_id.strip():
            raise ValueError("Lizenz-ID ist erforderlich.")
        if self.max_users <= 0:
            raise ValueError("Maximale Nutzerzahl muss größer als 0 sein.")
        if any(not feature.strip() for feature in self.features):
            raise ValueError("Lizenzfeatures dürfen nicht leer sein.")


@dataclass
class Absence:
    start: datetime
    end: datetime
    reason: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        self.reason = self.reason.strip()
        if self.end <= self.start:
            raise ValueError("Abwesenheitsende muss nach dem Start liegen.")

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return start < self.end and end > self.start


@dataclass
class Availability:
    start: datetime
    end: datetime

    def covers(self, shift: "Shift") -> bool:
        return self.start <= shift.start and self.end >= shift.end


@dataclass
class Shift:
    name: str
    department: str
    start: datetime
    end: datetime
    required_employees: int
    required_qualification: str = ""
    branch: str = "Zentrale"
    id: str = field(default_factory=lambda: str(uuid4()))
    employee_ids: List[str] = field(default_factory=list)
    employee_names: List[str] = field(default_factory=list)
    published_at: datetime | None = None
    published_by: str = ""

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.department = self.department.strip()
        self.required_qualification = self.required_qualification.strip()
        self.branch = self.branch.strip() or "Zentrale"
        if not self.name:
            raise ValueError("Schichtname ist erforderlich.")
        if not self.department:
            raise ValueError("Schichtabteilung ist erforderlich.")
        if self.end <= self.start:
            raise ValueError("Schichtende muss nach dem Start liegen.")
        if self.required_employees <= 0:
            raise ValueError("Schichtkapazität muss größer als 0 sein.")

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    @property
    def is_full(self) -> bool:
        return len(self.employee_ids) >= self.required_employees

    @property
    def occupancy_rate(self) -> float:
        if self.required_employees <= 0:
            return 0.0
        return min(1.0, len(self.employee_ids) / self.required_employees)


@dataclass
class Employee:
    name: str
    department: str
    qualification: str = ""
    weekly_hours_limit: int = 40
    branch: str = "Zentrale"
    hourly_wage: float = 15.0
    is_active: bool = True
    break_minutes_per_shift: int = 0
    id: str = field(default_factory=lambda: str(uuid4()))
    shifts: List[Shift] = field(default_factory=list)
    absences: List[Absence] = field(default_factory=list)
    availabilities: List[Availability] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.department = self.department.strip()
        self.qualification = self.qualification.strip()
        self.branch = self.branch.strip() or "Zentrale"
        if not self.name:
            raise ValueError("Mitarbeitername ist erforderlich.")
        if not self.department:
            raise ValueError("Mitarbeiterabteilung ist erforderlich.")
        if self.weekly_hours_limit <= 0:
            raise ValueError("Wochenstundenlimit muss größer als 0 sein.")
        if self.hourly_wage < 0:
            raise ValueError("Stundenlohn darf nicht negativ sein.")
        if self.break_minutes_per_shift < 0:
            raise ValueError("Pausenzeit darf nicht negativ sein.")

    def net_hours_for_shift(self, shift: Shift) -> float:
        """Return paid/planned working hours for a shift after this employee's break.

        Breaks are capped at the shift duration so invalid combinations never create
        negative planned hours in reports or limit checks.
        """
        break_hours = self.break_minutes_per_shift / 60
        return max(0.0, shift.duration_hours - break_hours)

    @property
    def planned_hours(self) -> float:
        return sum(self.net_hours_for_shift(shift) for shift in self.shifts)

    @property
    def overtime(self) -> float:
        return max(0.0, self.planned_hours - self.weekly_hours_limit)


@dataclass
class RuleProfile:
    """Configurable planning limits for a company or branch policy.

    Values are deliberately stored as primitive types so profiles can be
    persisted in SQLite without a migration framework. Hard violations block an
    assignment; warning-only rules are returned in AssignmentResult.warnings.
    """

    name: str = "Standardprofil"
    min_rest_hours: float = 11.0
    max_daily_hours: float = 10.0
    break_after_six_hours_minutes: int = 30
    break_after_nine_hours_minutes: int = 45
    weekly_hours_limit_is_hard: bool = True
    daily_hours_limit_is_hard: bool = True
    rest_time_is_hard: bool = True
    profile_mismatch_is_hard: bool = True
    missing_availability_is_hard: bool = False
    insufficient_break_is_hard: bool = False
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Profilname ist erforderlich.")
        if self.min_rest_hours < 0:
            raise ValueError("Mindestruhezeit darf nicht negativ sein.")
        if self.max_daily_hours <= 0:
            raise ValueError("Tageshöchstarbeitszeit muss größer als 0 sein.")
        if self.break_after_six_hours_minutes < 0 or self.break_after_nine_hours_minutes < 0:
            raise ValueError("Pausenwerte dürfen nicht negativ sein.")
        if self.break_after_nine_hours_minutes < self.break_after_six_hours_minutes:
            raise ValueError("Pause nach neun Stunden darf nicht kleiner als Pause nach sechs Stunden sein.")

    def required_break_minutes_for_hours(self, duration_hours: float) -> int:
        if duration_hours > 9:
            return self.break_after_nine_hours_minutes
        if duration_hours > 6:
            return self.break_after_six_hours_minutes
        return 0


@dataclass(frozen=True)
class AssignmentResult:
    success: bool
    errors: List[str]
    warnings: List[str]

    @property
    def message(self) -> str:
        if self.success:
            if self.warnings:
                return "Zuweisung erfolgreich mit Warnungen: " + "; ".join(self.warnings)
            return "Zuweisung erfolgreich"
        return "; ".join(self.errors) if self.errors else "Zuweisung fehlgeschlagen"


@dataclass(frozen=True)
class ReportMetric:
    category: str
    name: str
    value: str
    note: str = ""


@dataclass(frozen=True)
class RevenueForecast:
    branch_id: int
    branch: str
    date: datetime
    expected_revenue: float
    expected_customers: int
