from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import List

from .models import Employee, Shift


@dataclass
class RuleOutcome:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def extend(self, other: "RuleOutcome") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


class PlanningRules:
    """Central rule engine for shift assignments.

    Hard errors block an assignment. Warnings are shown but do not block it.
    The implementation deliberately keeps the rules deterministic and side-effect free.
    """

    MIN_REST = timedelta(hours=11)
    MAX_DAILY_HOURS = 10.0

    def validate_assignment(
        self,
        employee: Employee | None,
        shift: Shift | None,
        *,
        ignore_profile_mismatch: bool = False,
    ) -> RuleOutcome:
        result = RuleOutcome()
        if employee is None:
            result.errors.append("Es wurde kein Mitarbeiter ausgewählt.")
        if shift is None:
            result.errors.append("Es wurde keine Schicht ausgewählt.")
        if result.errors:
            return result

        assert employee is not None and shift is not None

        if not employee.is_active:
            result.errors.append("Der Mitarbeiter ist nicht aktiv.")
        if shift.is_full and employee.id not in shift.employee_ids:
            result.errors.append("Die Schicht ist bereits voll.")
        if employee.id in shift.employee_ids:
            result.errors.append("Der Mitarbeiter ist der Schicht bereits zugewiesen.")
        profile_warnings = self._validate_profile_match(employee, shift)
        if ignore_profile_mismatch:
            result.warnings.extend(profile_warnings)
        else:
            result.errors.extend(profile_warnings)
        if employee.planned_hours + shift.duration_hours > employee.weekly_hours_limit:
            result.errors.append("Wochenstundenlimit überschritten.")

        daily_hours = sum(s.duration_hours for s in employee.shifts if s.start.date() == shift.start.date()) + shift.duration_hours
        if daily_hours > self.MAX_DAILY_HOURS:
            result.errors.append("Tageshöchstarbeitszeit überschritten.")

        for existing in employee.shifts:
            if shift.start < existing.end and shift.end > existing.start:
                result.errors.append("Der Mitarbeiter hat in diesem Zeitraum bereits eine Schicht.")
                break

            if existing.end <= shift.start and shift.start - existing.end < self.MIN_REST:
                result.errors.append("Ruhezeit unterschritten.")
                break
            if shift.end <= existing.start and existing.start - shift.end < self.MIN_REST:
                result.errors.append("Ruhezeit unterschritten.")
                break

        for absence in employee.absences:
            if absence.overlaps(shift.start, shift.end):
                reason = absence.reason or "ohne Angabe"
                result.errors.append(f"Der Mitarbeiter ist im Schichtzeitraum abwesend ({reason}).")
                break

        if employee.availabilities and not any(a.covers(shift) for a in employee.availabilities):
            result.warnings.append("Für den Mitarbeiter ist keine passende Verfügbarkeit hinterlegt.")

        if shift.duration_hours > 9:
            result.warnings.append("Für Schichten über 9 Stunden sollte eine ausreichende Pause geplant werden.")
        elif shift.duration_hours > 6:
            result.warnings.append("Für Schichten über 6 Stunden sollte eine Pause geplant werden.")

        return result

    @staticmethod
    def _validate_profile_match(employee: Employee, shift: Shift) -> list[str]:
        """Return department, branch and qualification mismatches as reusable messages."""
        mismatches: list[str] = []
        if employee.department.lower() != shift.department.lower():
            mismatches.append("Die Abteilung des Mitarbeiters passt nicht zur Schicht.")
        if employee.branch.lower() != shift.branch.lower():
            mismatches.append("Die Filiale des Mitarbeiters passt nicht zur Schicht.")
        if shift.required_qualification and employee.qualification.lower() != shift.required_qualification.lower():
            mismatches.append("Die Qualifikation des Mitarbeiters passt nicht zur Schicht.")
        return mismatches
