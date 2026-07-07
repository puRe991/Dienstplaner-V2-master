from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from .models import Employee, ExportFormat, Shift


@dataclass(frozen=True)
class ExportOptions:
    """Privacy and scope controls for schedule exports.

    Defaults are deliberately compatible with the previous CSV export: wage data is
    hidden, absence reasons are visible in plan-specific exports, and unpublished
    shifts are included unless callers request a publication-only export.
    """

    include_hourly_wage: bool = False
    include_absence_reason: bool = True
    only_published_shifts: bool = False
    anonymize_employee_names: bool = False


class ExportPrivacyProfile(str, Enum):
    """Fixed export privacy profiles for the schedule export dialog.

    The MVP intentionally ships three fixed profiles instead of a freely
    configurable field matrix, so callers pick a purpose instead of assembling
    ``ExportOptions`` by hand.
    """

    INTERNAL_FULL = "internal_full"
    EMPLOYEE_PLAN_REDUCED = "employee_plan_reduced"
    CONTROLLING_ANONYMIZED = "controlling_anonymized"


EXPORT_PRIVACY_PROFILE_LABELS: dict[ExportPrivacyProfile, str] = {
    ExportPrivacyProfile.INTERNAL_FULL: "Intern vollständig",
    ExportPrivacyProfile.EMPLOYEE_PLAN_REDUCED: "Mitarbeitendenplan reduziert",
    ExportPrivacyProfile.CONTROLLING_ANONYMIZED: "Controlling anonymisiert",
}

EXPORT_PRIVACY_PROFILE_DESCRIPTIONS: dict[ExportPrivacyProfile, str] = {
    ExportPrivacyProfile.INTERNAL_FULL: (
        "Vollständiger interner Export mit Stundenlöhnen, Abwesenheitsgründen und "
        "allen Schichten, auch unveröffentlichten. Nur für internen Gebrauch weitergeben."
    ),
    ExportPrivacyProfile.EMPLOYEE_PLAN_REDUCED: (
        "Reduzierter Plan für Mitarbeitende: keine Löhne, keine Abwesenheitsgründe, "
        "nur bereits veröffentlichte Schichten."
    ),
    ExportPrivacyProfile.CONTROLLING_ANONYMIZED: (
        "Anonymisierter Export für Controlling: Personalkosten bleiben sichtbar, "
        "Mitarbeitendennamen werden anonymisiert und Abwesenheitsgründe entfernt."
    ),
}


def export_options_for_profile(profile: ExportPrivacyProfile) -> ExportOptions:
    """Return the fixed ``ExportOptions`` for one of the MVP privacy profiles."""
    if profile == ExportPrivacyProfile.INTERNAL_FULL:
        return ExportOptions(include_hourly_wage=True, include_absence_reason=True, only_published_shifts=False)
    if profile == ExportPrivacyProfile.EMPLOYEE_PLAN_REDUCED:
        return ExportOptions(include_hourly_wage=False, include_absence_reason=False, only_published_shifts=True)
    if profile == ExportPrivacyProfile.CONTROLLING_ANONYMIZED:
        return ExportOptions(
            include_hourly_wage=True,
            include_absence_reason=False,
            only_published_shifts=False,
            anonymize_employee_names=True,
        )
    raise ValueError(f"Unbekanntes Exportprofil: {profile}")


@dataclass(frozen=True)
class ExportHeader:
    company_name: str = "Dienstplanung Pro"
    period: str = "Alle Schichten"
    created_at: datetime | None = None
    created_by: str = "Lokaler Modus"

    def normalized_company_name(self) -> str:
        return self.company_name.strip() or "Dienstplanung Pro"

    def normalized_created_by(self) -> str:
        return self.created_by.strip() or "Lokaler Modus"


class ScheduleExporter:
    """Exports schedule data without coupling it to SchedulerService state logic."""

    def __init__(self, employees: Sequence[Employee], shifts: Sequence[Shift]) -> None:
        self.employees = list(employees)
        self.shifts = list(shifts)

    def export_schedule(
        self,
        path: str | Path,
        export_format: ExportFormat = ExportFormat.CSV,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        rows = self._shift_rows(self._filtered_shifts(options), options or ExportOptions())
        columns = self._shift_columns(options or ExportOptions())
        return TabularExporter(columns, rows, header or ExportHeader()).export(path, export_format)

    def export_week_plan_pdf(
        self,
        path: str | Path,
        week_start: datetime,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        start = datetime.combine(week_start.date(), time.min)
        end = start + timedelta(days=7)
        selected = self._filtered_shifts(options, start=start, end=end)
        export_header = self._header_with_period(header, f"{start:%d.%m.%Y} - {(end - timedelta(days=1)):%d.%m.%Y}")
        rows = self._shift_rows(selected, options or ExportOptions())
        return TabularExporter(self._shift_columns(options or ExportOptions()), rows, export_header).export(path, ExportFormat.PDF)

    def export_day_plan_pdf(
        self,
        path: str | Path,
        day: datetime,
        *,
        options: ExportOptions | None = None,
        header: ExportHeader | None = None,
    ) -> Path:
        start = datetime.combine(day.date(), time.min)
        end = start + timedelta(days=1)
        selected = self._filtered_shifts(options, start=start, end=end)
        export_header = self._header_with_period(header, f"{start:%d.%m.%Y}")
        rows = self._shift_rows(selected, options or ExportOptions())
        return TabularExporter(self._shift_columns(options or ExportOptions()), rows, export_header).export(path, ExportFormat.PDF)

    def export_ics(
        self,
        path: str | Path,
        start: datetime,
        end: datetime,
        *,
        employee_id: str | None = None,
        options: ExportOptions | None = None,
    ) -> Path:
        """Export shifts in ``[start, end)`` as an iCalendar (.ics) file.

        Times are written as floating local time (no TZID/UTC conversion)
        since the application does not track a per-installation timezone.
        Most calendar clients interpret floating time as the device's local
        time, which matches how shift times are entered and displayed here.
        """
        if end <= start:
            raise ValueError("Exportzeitraum muss nach dem Start enden.")
        export_options = options or ExportOptions()
        employee = None
        if employee_id is not None:
            employee = self._find_employee(employee_id)
            if employee is None:
                raise ValueError("Mitarbeiter wurde nicht gefunden.")

        selected = self._filtered_shifts(export_options, start=start, end=end)
        if employee is not None:
            selected = [shift for shift in selected if employee.id in shift.employee_ids]

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(IcsCalendarDocument(selected, employee, export_options).render())
        return output

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
        if period_end <= period_start:
            raise ValueError("Exportzeitraum muss nach dem Start enden.")
        employee = self._find_employee(employee_id)
        if employee is None:
            raise ValueError("Mitarbeiter wurde nicht gefunden.")
        export_options = options or ExportOptions()
        shifts = [shift for shift in self._filtered_shifts(export_options, start=period_start, end=period_end) if employee.id in shift.employee_ids]
        rows = self._employee_rows(employee, shifts, period_start, period_end, export_options)
        columns = ["Mitarbeiter", "Abteilung", "Datum", "Schicht", "Start", "Ende", "Stunden"]
        if export_options.include_hourly_wage:
            columns.append("Stundenlohn")
        columns.append("Abwesenheit")
        export_header = self._header_with_period(header, f"{period_start:%d.%m.%Y} - {period_end:%d.%m.%Y}")
        return TabularExporter(columns, rows, export_header).export(path, ExportFormat.PDF)

    @staticmethod
    def _header_with_period(header: ExportHeader | None, period: str) -> ExportHeader:
        if header is None:
            return ExportHeader(period=period)
        if header.period == ExportHeader().period:
            return replace(header, period=period)
        return header

    def _find_employee(self, employee_id: str) -> Employee | None:
        return next((employee for employee in self.employees if employee.id == employee_id), None)

    def _filtered_shifts(
        self,
        options: ExportOptions | None,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Shift]:
        export_options = options or ExportOptions()
        selected = []
        for shift in self.shifts:
            if export_options.only_published_shifts and shift.published_at is None:
                continue
            if start is not None and shift.start < start:
                continue
            if end is not None and shift.start >= end:
                continue
            selected.append(shift)
        return sorted(selected, key=lambda item: (item.start, item.name))

    def _shift_columns(self, options: ExportOptions) -> list[str]:
        columns = ["Schicht", "Abteilung", "Filiale", "Start", "Ende", "Kapazität", "Mitarbeitende"]
        if options.include_hourly_wage:
            columns.append("Stundenlohn")
        return columns

    def _shift_rows(self, shifts: Iterable[Shift], options: ExportOptions) -> list[list[str]]:
        rows: list[list[str]] = []
        for shift in shifts:
            if options.anonymize_employee_names:
                assigned_display = ", ".join(f"Mitarbeiter {index + 1}" for index in range(len(shift.employee_names)))
            else:
                assigned_display = ", ".join(shift.employee_names)
            row = [
                shift.name,
                shift.department,
                shift.branch,
                shift.start.isoformat(sep=" ", timespec="minutes"),
                shift.end.isoformat(sep=" ", timespec="minutes"),
                str(shift.required_employees),
                assigned_display or "nicht besetzt",
            ]
            if options.include_hourly_wage:
                wages = [self._format_wage(employee.hourly_wage) for employee in self._assigned_employees(shift)]
                row.append(", ".join(wages) if wages else "-")
            rows.append(row)
        return rows

    def _employee_rows(
        self,
        employee: Employee,
        shifts: Sequence[Shift],
        period_start: datetime,
        period_end: datetime,
        options: ExportOptions,
    ) -> list[list[str]]:
        rows: list[list[str]] = []
        for shift in shifts:
            row = [
                employee.name,
                employee.department,
                shift.start.strftime("%d.%m.%Y"),
                shift.name,
                shift.start.strftime("%H:%M"),
                shift.end.strftime("%H:%M"),
                f"{employee.net_hours_for_shift(shift):.2f}",
            ]
            if options.include_hourly_wage:
                row.append(self._format_wage(employee.hourly_wage))
            row.append("")
            rows.append(row)

        for absence in sorted(employee.absences, key=lambda item: item.start):
            if not absence.overlaps(period_start, period_end):
                continue
            row = [
                employee.name,
                employee.department,
                absence.start.strftime("%d.%m.%Y"),
                "-",
                absence.start.strftime("%H:%M"),
                absence.end.strftime("%H:%M"),
                "0.00",
            ]
            if options.include_hourly_wage:
                row.append("")
            row.append(absence.reason if options.include_absence_reason and absence.reason else "Abwesend")
            rows.append(row)
        return sorted(rows, key=lambda row: (row[2], row[4], row[3]))

    def _assigned_employees(self, shift: Shift) -> list[Employee]:
        by_id = {employee.id: employee for employee in self.employees}
        return [by_id[employee_id] for employee_id in shift.employee_ids if employee_id in by_id]

    @staticmethod
    def _format_wage(value: float) -> str:
        return f"{value:.2f} EUR"


class TabularExporter:
    def __init__(self, columns: Sequence[str], rows: Sequence[Sequence[object]], header: ExportHeader) -> None:
        self.columns = [str(column) for column in columns]
        self.rows = [[str(cell) for cell in row] for row in rows]
        self.header = header

    def export(self, path: str | Path, export_format: ExportFormat) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if export_format == ExportFormat.PDF:
            output.write_bytes(SimplePdfDocument(self._pdf_lines()).render())
            return output
        if export_format == ExportFormat.PDF_TEXT:
            output.write_text("\n".join(self._pdf_lines()) + "\n", encoding="utf-8")
            return output
        delimiter = ";" if export_format in {ExportFormat.CSV, ExportFormat.EXCEL_COMPATIBLE} else ","
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=delimiter)
            writer.writerow(self.columns)
            writer.writerows(self.rows)
        return output

    def _pdf_lines(self) -> list[str]:
        created_at = self.header.created_at or datetime.now()
        lines = [
            self.header.normalized_company_name(),
            f"Zeitraum: {self.header.period}",
            f"Erstellt am: {created_at:%d.%m.%Y %H:%M}",
            f"Erstellt von: {self.header.normalized_created_by()}",
            "",
            " | ".join(self.columns),
            "-" * min(120, max(10, len(" | ".join(self.columns)))),
        ]
        if not self.rows:
            lines.append("Keine Einträge im gewählten Zeitraum.")
            return lines
        lines.extend(" | ".join(row) for row in self.rows)
        return lines


class IcsCalendarDocument:
    """Minimal dependency-free iCalendar (RFC 5545) writer for shift exports.

    Times are written as floating local time (no TZID, no UTC conversion)
    since the application does not track a per-installation timezone; most
    calendar clients interpret floating time as the device's local time.
    """

    PRODID = "-//Dienstplanung Pro//Schichtexport//DE"
    LINE_FOLD_LENGTH = 75

    def __init__(self, shifts: Sequence[Shift], employee: Employee | None, options: ExportOptions) -> None:
        self.shifts = list(shifts)
        self.employee = employee
        self.options = options

    def render(self) -> bytes:
        now = datetime.now()
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{self.PRODID}", "CALSCALE:GREGORIAN"]
        for shift in sorted(self.shifts, key=lambda item: (item.start, item.name)):
            lines.extend(self._event_lines(shift, now))
        lines.append("END:VCALENDAR")

        folded: list[str] = []
        for line in lines:
            folded.extend(self._fold_line(line))
        return ("\r\n".join(folded) + "\r\n").encode("utf-8")

    def _event_lines(self, shift: Shift, now: datetime) -> list[str]:
        summary = shift.name if self.employee is None else f"{shift.name} ({shift.department})"
        assigned = self._assigned_names(shift)
        description_parts = [f"Abteilung: {shift.department}", f"Filiale: {shift.branch}"]
        if assigned:
            description_parts.append(f"Mitarbeitende: {', '.join(assigned)}")
        return [
            "BEGIN:VEVENT",
            f"UID:{shift.id}@dienstplanung-pro",
            f"DTSTAMP:{self._format_utc(now)}",
            f"DTSTART:{self._format_floating(shift.start)}",
            f"DTEND:{self._format_floating(shift.end)}",
            f"SUMMARY:{self._escape(summary)}",
            f"LOCATION:{self._escape(shift.branch)}",
            f"DESCRIPTION:{self._escape(chr(10).join(description_parts))}",
            "END:VEVENT",
        ]

    def _assigned_names(self, shift: Shift) -> list[str]:
        if not self.options.anonymize_employee_names:
            return list(shift.employee_names)
        return [f"Mitarbeiter {index + 1}" for index in range(len(shift.employee_names))]

    @staticmethod
    def _format_floating(value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%S")

    @staticmethod
    def _format_utc(value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    @classmethod
    def _fold_line(cls, line: str) -> list[str]:
        encoded = line.encode("utf-8")
        if len(encoded) <= cls.LINE_FOLD_LENGTH:
            return [line]
        chunks: list[str] = []
        start = 0
        limit = cls.LINE_FOLD_LENGTH
        while start < len(encoded):
            chunk = encoded[start : start + limit]
            while chunk:
                try:
                    chunks.append(chunk.decode("utf-8"))
                    break
                except UnicodeDecodeError:
                    chunk = chunk[:-1]
            start += len(chunk)
            limit = cls.LINE_FOLD_LENGTH - 1
        return [chunks[0]] + [f" {chunk}" for chunk in chunks[1:]]


class SimplePdfDocument:
    """Small, dependency-free PDF writer for text-based tabular exports."""

    PAGE_WIDTH = 842
    PAGE_HEIGHT = 595
    LEFT = 36
    TOP = 555
    LINE_HEIGHT = 14
    MAX_CHARS = 135

    def __init__(self, lines: Sequence[str]) -> None:
        self.lines = list(lines)

    def render(self) -> bytes:
        pages = self._paginate()
        objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
        page_refs = []
        for index, page_lines in enumerate(pages):
            page_obj = 3 + index * 2
            content_obj = page_obj + 1
            page_refs.append(f"{page_obj} 0 R")
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.PAGE_WIDTH} {self.PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
                f"/Contents {content_obj} 0 R >>".encode("ascii")
            )
            stream = self._content_stream(page_lines)
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream")
        pages_object = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>".encode("ascii")
        objects.insert(1, pages_object)
        return self._serialize(objects)

    def _paginate(self) -> list[list[str]]:
        wrapped: list[str] = []
        for line in self.lines:
            chunks = self._wrap(line)
            wrapped.extend(chunks or [""])
        lines_per_page = max(1, int((self.TOP - 36) / self.LINE_HEIGHT))
        return [wrapped[index : index + lines_per_page] for index in range(0, len(wrapped), lines_per_page)] or [[""]]

    def _wrap(self, line: str) -> list[str]:
        if len(line) <= self.MAX_CHARS:
            return [line]
        chunks = []
        remaining = line
        while len(remaining) > self.MAX_CHARS:
            split_at = remaining.rfind(" ", 0, self.MAX_CHARS)
            if split_at <= 0:
                split_at = self.MAX_CHARS
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()
        if remaining:
            chunks.append(remaining)
        return chunks

    def _content_stream(self, lines: Sequence[str]) -> bytes:
        commands = ["BT", "/F1 9 Tf", f"{self.LEFT} {self.TOP} Td"]
        for index, line in enumerate(lines):
            if index:
                commands.append(f"0 -{self.LINE_HEIGHT} Td")
            commands.append(f"({self._escape_pdf_text(line)}) Tj")
        commands.append("ET")
        return ("\n".join(commands) + "\n").encode("cp1252", errors="replace")

    def _escape_pdf_text(self, text: str) -> str:
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return safe

    def _serialize(self, objects: Sequence[bytes]) -> bytes:
        result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for number, payload in enumerate(objects, start=1):
            offsets.append(len(result))
            result.extend(f"{number} 0 obj\n".encode("ascii"))
            result.extend(payload)
            result.extend(b"\nendobj\n")
        xref_offset = len(result)
        result.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        result.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            result.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        result.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        return bytes(result)
