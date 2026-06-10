from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import List

from .models import Employee, RuleProfile, Shift


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
    The active RuleProfile defines legal/company-specific thresholds and whether
    selected checks are blocking or advisory.
    """

    def __init__(self, profile: RuleProfile | None = None) -> None:
        self.profile = profile or RuleProfile()

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

        profile_mismatches = self._validate_profile_match(employee, shift)
        if ignore_profile_mismatch:
            result.warnings.extend(profile_mismatches)
        else:
            self._add_configured(result, profile_mismatches, self.profile.profile_mismatch_is_hard)

        shift_net_hours = employee.net_hours_for_shift(shift)
        if employee.planned_hours + shift_net_hours > employee.weekly_hours_limit:
            self._add_configured(result, ["Wochenstundenlimit überschritten."], self.profile.weekly_hours_limit_is_hard)

        daily_hours = sum(employee.net_hours_for_shift(s) for s in employee.shifts if s.start.date() == shift.start.date()) + shift_net_hours
        if daily_hours > self.profile.max_daily_hours:
            self._add_configured(result, ["Tageshöchstarbeitszeit überschritten."], self.profile.daily_hours_limit_is_hard)

        min_rest = timedelta(hours=self.profile.min_rest_hours)
        overlap_reported = False
        rest_time_reported = False
        # Always scan every assigned shift: rest violations can be warnings,
        # but overlaps must remain hard blockers.
        for existing in employee.shifts:
            if self._shifts_overlap(existing, shift):
                if not overlap_reported:
                    result.errors.append("Der Mitarbeiter hat in diesem Zeitraum bereits eine Schicht.")
                    overlap_reported = True
                continue

            if not rest_time_reported and self._violates_min_rest(existing, shift, min_rest):
                self._add_configured(result, ["Ruhezeit unterschritten."], self.profile.rest_time_is_hard)
                rest_time_reported = True

        for absence in employee.absences:
            if absence.overlaps(shift.start, shift.end):
                reason = absence.reason or "ohne Angabe"
                result.errors.append(f"Der Mitarbeiter ist im Schichtzeitraum abwesend ({reason}).")
                break

        if employee.availabilities and not any(a.covers(shift) for a in employee.availabilities):
            self._add_configured(
                result,
                ["Für den Mitarbeiter ist keine passende Verfügbarkeit hinterlegt."],
                self.profile.missing_availability_is_hard,
            )

        required_break_minutes = self.required_break_minutes(shift)
        if employee.break_minutes_per_shift < required_break_minutes:
            self._add_configured(
                result,
                [
                    f"Pausenzeit prüfen: Für diese Schicht sind mindestens {required_break_minutes} Minuten Pause empfohlen. "
                    f"Beim Mitarbeiter sind {employee.break_minutes_per_shift} Minuten hinterlegt."
                ],
                self.profile.insufficient_break_is_hard,
            )

        return result

    def required_break_minutes(self, shift: Shift) -> int:
        """Return the minimum break recommendation for a shift duration."""
        return self.profile.required_break_minutes_for_hours(shift.duration_hours)

    @staticmethod
    def _shifts_overlap(existing: Shift, candidate: Shift) -> bool:
        return candidate.start < existing.end and candidate.end > existing.start

    @staticmethod
    def _violates_min_rest(existing: Shift, candidate: Shift, min_rest: timedelta) -> bool:
        candidate_after_existing = (
            existing.end <= candidate.start and candidate.start - existing.end < min_rest
        )
        candidate_before_existing = (
            candidate.end <= existing.start and existing.start - candidate.end < min_rest
        )
        return candidate_after_existing or candidate_before_existing

    @staticmethod
    def _add_configured(result: RuleOutcome, messages: list[str], is_hard: bool) -> None:
        if is_hard:
            result.errors.extend(messages)
        else:
            result.warnings.extend(messages)

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
