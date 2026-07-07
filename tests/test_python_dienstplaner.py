from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_dienstplaner.auth import Permission, User, UserRole
from python_dienstplaner.exporters import (
    EXPORT_PRIVACY_PROFILE_LABELS,
    ExportHeader,
    ExportOptions,
    ExportPrivacyProfile,
    export_options_for_profile,
)
from python_dienstplaner.models import DEFAULT_ABSENCE_REASONS, Absence, ExportFormat, RuleProfile
from python_dienstplaner.repository import SCHEMA_VERSION, SQLiteSchedulerRepository
from python_dienstplaner.services import DEFAULT_RETAIL_DEPARTMENTS, ForecastImportService, SchedulerService


TEST_LICENSE_RSA_MODULUS = int(
    "c0d244d118c03575f1395b8a559b4e31cf7df01c015a08d35d496b375a9d05"
    "a3e5b9138979ee26437e691e19c36e8bea751d96dd6c3445e28126768ece"
    "e0ff71cabc2f08a4f8397d9353971e1a26e385a4561b847347bf314ddb"
    "b22f00326ba958d2710d8fc6ba52569b22a095acee105cdbabba9762ac66"
    "0a57546b501d41ed",
    16,
)
TEST_LICENSE_RSA_PUBLIC_EXPONENT = 65537
TEST_LICENSE_RSA_PRIVATE_EXPONENT = int(
    "2a24cb0db88f2a20211d1c38dc0519ce213fb15f2d9c74195e66519cc39d"
    "5642404f7749b0f0b0444838c96f701b9551254fd64d86fcd5d96fc8ec58"
    "c236c31dc674e040d674c617b684b718f5df5e129a819c58f24c55a97243"
    "1845860b6452e6128ff1ef0d5f734581cab4b8dfc553833b20b6c5372ea1"
    "63c34c93d22abeb1",
    16,
)


class SchedulerServiceTests(unittest.TestCase):
    def test_service_exposes_default_retail_departments_and_custom_options(self) -> None:
        service = SchedulerService()

        service.add_department("Non-Food")

        self.assertIn("Kasse", service.department_options())
        self.assertIn("Lager / Wareneingang", service.department_options())
        self.assertIn("Non-Food", service.department_options())
        self.assertGreaterEqual(len(service.department_options()), len(DEFAULT_RETAIL_DEPARTMENTS))

    def test_copy_shift_reuses_shift_data_without_assignments(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        self.assertTrue(service.assign(employee.id, shift.id).success)

        copied = service.copy_shift(shift.id, datetime(2026, 1, 2, 8), datetime(2026, 1, 2, 16))

        self.assertNotEqual(shift.id, copied.id)
        self.assertEqual("Früh", copied.name)
        self.assertEqual("Kasse", copied.department)
        self.assertEqual([], copied.employee_ids)
        self.assertEqual([], copied.employee_names)

    def test_assigns_employee_when_rules_are_satisfied(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        result = service.assign(employee.id, shift.id)

        self.assertTrue(result.success)
        self.assertEqual([employee.id], shift.employee_ids)
        self.assertEqual([shift], employee.shifts)

    def test_blocks_assignment_when_shift_is_full(self) -> None:
        service = SchedulerService()
        first = service.add_employee("Eva Retail", "Kasse", "Kasse")
        second = service.add_employee("Max Muster", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        self.assertTrue(service.assign(first.id, shift.id).success)

        result = service.assign(second.id, shift.id)

        self.assertFalse(result.success)
        self.assertIn("Die Schicht ist bereits voll.", result.errors)

    def test_blocks_profile_mismatch_by_default(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", branch="Zentrale")
        shift = service.add_shift(
            "Wareneingang",
            "Lager",
            datetime(2026, 1, 1, 8),
            datetime(2026, 1, 1, 16),
            1,
            "Staplerschein",
            branch="Filiale Nord",
        )

        result = service.assign(employee.id, shift.id)

        self.assertFalse(result.success)
        self.assertIn("Die Abteilung des Mitarbeiters passt nicht zur Schicht.", result.errors)
        self.assertIn("Die Filiale des Mitarbeiters passt nicht zur Schicht.", result.errors)
        self.assertIn("Die Qualifikation des Mitarbeiters passt nicht zur Schicht.", result.errors)

    def test_can_assign_employee_while_ignoring_department_branch_and_qualification(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", branch="Zentrale")
        shift = service.add_shift(
            "Wareneingang",
            "Lager",
            datetime(2026, 1, 1, 8),
            datetime(2026, 1, 1, 16),
            1,
            "Staplerschein",
            branch="Filiale Nord",
        )

        result = service.assign(employee.id, shift.id, ignore_profile_mismatch=True)

        self.assertTrue(result.success)
        self.assertEqual([employee.id], shift.employee_ids)
        self.assertEqual([shift], employee.shifts)
        self.assertIn("Die Abteilung des Mitarbeiters passt nicht zur Schicht.", result.warnings)
        self.assertIn("Die Filiale des Mitarbeiters passt nicht zur Schicht.", result.warnings)
        self.assertIn("Die Qualifikation des Mitarbeiters passt nicht zur Schicht.", result.warnings)

    def test_blocks_overlapping_absence(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        employee.absences.append(Absence(datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 12), "Urlaub"))
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        result = service.assign(employee.id, shift.id)

        self.assertFalse(result.success)
        self.assertIn("Der Mitarbeiter ist im Schichtzeitraum abwesend (Urlaub).", result.errors)

    def test_soft_rest_warning_still_checks_later_overlapping_shift(self) -> None:
        service = SchedulerService(
            rule_profiles=[
                RuleProfile(
                    name="Flexible Ruhezeit",
                    min_rest_hours=11,
                    max_daily_hours=24,
                    rest_time_is_hard=False,
                    break_after_six_hours_minutes=0,
                    break_after_nine_hours_minutes=0,
                )
            ]
        )
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        early_shift = service.add_shift(
            "Früh", "Kasse", datetime(2026, 1, 1, 0), datetime(2026, 1, 1, 7), 1, "Kasse"
        )
        overlapping_shift = service.add_shift(
            "Mitte", "Kasse", datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 14), 1, "Kasse"
        )
        candidate_shift = service.add_shift(
            "Spät", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 12), 1, "Kasse"
        )
        self.assertTrue(service.assign(employee.id, early_shift.id).success)
        self.assertTrue(service.assign(employee.id, overlapping_shift.id).success)

        result = service.assign(employee.id, candidate_shift.id)

        self.assertFalse(result.success)
        self.assertIn("Ruhezeit unterschritten.", result.warnings)
        self.assertIn("Der Mitarbeiter hat in diesem Zeitraum bereits eine Schicht.", result.errors)
        self.assertNotIn(employee.id, candidate_shift.employee_ids)

    def test_hard_rest_error_still_reports_later_overlapping_shift(self) -> None:
        service = SchedulerService(
            rule_profiles=[
                RuleProfile(
                    name="Strenge Ruhezeit",
                    min_rest_hours=11,
                    max_daily_hours=24,
                    rest_time_is_hard=True,
                    break_after_six_hours_minutes=0,
                    break_after_nine_hours_minutes=0,
                )
            ]
        )
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        employee.shifts.extend(
            [
                service.add_shift(
                    "Früh", "Kasse", datetime(2026, 1, 1, 0), datetime(2026, 1, 1, 7), 1, "Kasse"
                ),
                service.add_shift(
                    "Mitte", "Kasse", datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 14), 1, "Kasse"
                ),
            ]
        )
        candidate_shift = service.add_shift(
            "Spät", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 12), 1, "Kasse"
        )

        result = service.assign(employee.id, candidate_shift.id)

        self.assertFalse(result.success)
        self.assertIn("Ruhezeit unterschritten.", result.errors)
        self.assertIn("Der Mitarbeiter hat in diesem Zeitraum bereits eine Schicht.", result.errors)
        self.assertNotIn(employee.id, candidate_shift.employee_ids)

    def test_default_absence_reasons_include_common_unavailability_types(self) -> None:
        self.assertIn("Urlaub", DEFAULT_ABSENCE_REASONS)
        self.assertIn("Freier Tag", DEFAULT_ABSENCE_REASONS)
        self.assertIn("Krank", DEFAULT_ABSENCE_REASONS)
        self.assertIn("Fortbildung", DEFAULT_ABSENCE_REASONS)
        self.assertIn("Seminar", DEFAULT_ABSENCE_REASONS)

    def test_add_absence_accepts_predefined_non_vacation_reason(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")

        absence = service.add_absence(employee.id, datetime(2026, 1, 2), datetime(2026, 1, 3), "Freier Tag")

        self.assertEqual("Freier Tag", absence.reason)
        self.assertEqual([absence], employee.absences)

    def test_unassign_removes_employee_and_shift_links(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        self.assertTrue(service.unassign(employee.id, shift.id))

        self.assertEqual([], employee.shifts)
        self.assertEqual([], shift.employee_ids)
        self.assertEqual([], shift.employee_names)


    def test_employee_break_reduces_planned_hours_and_allows_weekly_limit_fit(self) -> None:
        service = SchedulerService()
        employee = service.add_employee(
            "Eva Retail",
            "Kasse",
            "Kasse",
            weekly_hours_limit=7,
            branch="Zentrale",
            break_minutes_per_shift=60,
        )
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        result = service.assign(employee.id, shift.id)

        self.assertTrue(result.success)
        self.assertEqual(7.0, employee.planned_hours)


    def test_rule_profile_can_turn_daily_limit_into_warning(self) -> None:
        service = SchedulerService(rule_profiles=[RuleProfile(name="Startup", max_daily_hours=6, daily_hours_limit_is_hard=False)])
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Lang", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        result = service.assign(employee.id, shift.id)

        self.assertTrue(result.success)
        self.assertIn("Tageshöchstarbeitszeit überschritten.", result.warnings)
        self.assertEqual([], result.errors)

    def test_rule_profile_can_keep_daily_limit_hard_for_strict_company(self) -> None:
        service = SchedulerService(rule_profiles=[RuleProfile(name="Tarifbetrieb", max_daily_hours=6, daily_hours_limit_is_hard=True)])
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Lang", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        result = service.assign(employee.id, shift.id)

        self.assertFalse(result.success)
        self.assertIn("Tageshöchstarbeitszeit überschritten.", result.errors)

    def test_rule_profile_controls_break_warning_threshold(self) -> None:
        service = SchedulerService(rule_profiles=[RuleProfile(name="Kurzpause", break_after_six_hours_minutes=15, break_after_nine_hours_minutes=30)])
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", break_minutes_per_shift=15)
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        result = service.assign(employee.id, shift.id)

        self.assertTrue(result.success)
        self.assertNotIn("Pausenzeit prüfen", result.message)

    def test_employee_break_must_not_be_negative(self) -> None:
        service = SchedulerService()

        with self.assertRaises(ValueError):
            service.add_employee("Eva Retail", "Kasse", break_minutes_per_shift=-1)

    def test_exports_schedule_as_csv(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        with tempfile.TemporaryDirectory() as directory:
            output = service.export_schedule(Path(directory) / "dienstplan.csv", ExportFormat.CSV)
            content = output.read_text(encoding="utf-8")

        self.assertIn("Schicht;Abteilung;Filiale;Start;Ende;Kapazität;Mitarbeitende", content)
        self.assertIn("Eva Retail", content)

    def test_exports_empty_week_plan_as_real_pdf_with_header(self) -> None:
        service = SchedulerService()

        with tempfile.TemporaryDirectory() as directory:
            output = service.export_week_plan_pdf(
                Path(directory) / "leer.pdf",
                datetime(2026, 1, 5),
                header=ExportHeader(company_name="Muster GmbH", created_at=datetime(2026, 1, 6, 9, 30), created_by="Admin"),
            )
            content = output.read_bytes()

        self.assertTrue(content.startswith(b"%PDF-1.4"))
        self.assertIn("Muster GmbH".encode("cp1252"), content)
        self.assertIn("Keine Eintr".encode("cp1252"), content)

    def test_week_pdf_handles_special_characters(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Zoë Müller", "Frische / Kühlung", "Käse", hourly_wage=17.5)
        shift = service.add_shift("Spät & Käse (Süd)", "Frische / Kühlung", datetime(2026, 1, 6, 12), datetime(2026, 1, 6, 20), 1, "Käse")
        service.assign(employee.id, shift.id)

        with tempfile.TemporaryDirectory() as directory:
            output = service.export_week_plan_pdf(
                Path(directory) / "sonderzeichen.pdf",
                datetime(2026, 1, 5),
                header=ExportHeader(company_name="Bäckerei & Co.", period="KW 02", created_at=datetime(2026, 1, 6, 9), created_by="Jörg Admin"),
            )
            content = output.read_bytes()

        self.assertIn("Zoë Müller".encode("cp1252"), content)
        self.assertIn("Spät & Käse \\(Süd\\)".encode("cp1252"), content)

    def test_export_privacy_filters_wage_absence_reason_and_unpublished_shifts(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", hourly_wage=99.99)
        employee.absences.append(Absence(datetime(2026, 1, 7, 8), datetime(2026, 1, 7, 16), "Krank"))
        unpublished = service.add_shift("Unveröffentlicht", "Kasse", datetime(2026, 1, 7, 8), datetime(2026, 1, 7, 16), 1, "Kasse")
        published = service.add_shift("Veröffentlicht", "Kasse", datetime(2026, 1, 8, 8), datetime(2026, 1, 8, 16), 1, "Kasse")
        service.assign(employee.id, unpublished.id)
        service.assign(employee.id, published.id)
        published.published_at = datetime(2026, 1, 8, 10)
        published.published_by = "Planerin"

        with tempfile.TemporaryDirectory() as directory:
            weekly = service.export_schedule(
                Path(directory) / "published.csv",
                ExportFormat.CSV,
                options=ExportOptions(include_hourly_wage=False, only_published_shifts=True),
            ).read_text(encoding="utf-8")
            employee_pdf = service.export_employee_plan_pdf(
                Path(directory) / "employee.pdf",
                employee.id,
                datetime(2026, 1, 5),
                datetime(2026, 1, 12),
                options=ExportOptions(include_hourly_wage=False, include_absence_reason=False),
            ).read_bytes()

        self.assertIn("Veröffentlicht", weekly)
        self.assertNotIn("Unveröffentlicht", weekly)
        self.assertNotIn("Stundenlohn", weekly)
        self.assertNotIn(b"99.99", employee_pdf)
        self.assertNotIn(b"Krank", employee_pdf)
        self.assertIn(b"Abwesend", employee_pdf)

    def test_export_columns_respect_options(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", hourly_wage=18.25)
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        with tempfile.TemporaryDirectory() as directory:
            without_wage = service.export_schedule(Path(directory) / "ohne.csv", ExportFormat.CSV).read_text(encoding="utf-8").splitlines()[0]
            with_wage = service.export_schedule(
                Path(directory) / "mit.csv",
                ExportFormat.CSV,
                options=ExportOptions(include_hourly_wage=True),
            ).read_text(encoding="utf-8").splitlines()[0]

        self.assertEqual("Schicht;Abteilung;Filiale;Start;Ende;Kapazität;Mitarbeitende", without_wage)
        self.assertEqual("Schicht;Abteilung;Filiale;Start;Ende;Kapazität;Mitarbeitende;Stundenlohn", with_wage)

    def test_controlling_anonymized_profile_replaces_employee_names_but_keeps_wage(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", hourly_wage=18.25)
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        options = export_options_for_profile(ExportPrivacyProfile.CONTROLLING_ANONYMIZED)
        with tempfile.TemporaryDirectory() as directory:
            content = service.export_schedule(
                Path(directory) / "controlling.csv", ExportFormat.CSV, options=options
            ).read_text(encoding="utf-8")

        self.assertNotIn("Eva Retail", content)
        self.assertIn("Mitarbeiter 1", content)
        self.assertIn("18.25", content)

    def test_employee_plan_reduced_profile_hides_wage_and_unpublished_shifts(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", hourly_wage=18.25)
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        options = export_options_for_profile(ExportPrivacyProfile.EMPLOYEE_PLAN_REDUCED)
        with tempfile.TemporaryDirectory() as directory:
            content = service.export_schedule(
                Path(directory) / "employee_plan.csv", ExportFormat.CSV, options=options
            ).read_text(encoding="utf-8")

        self.assertNotIn("18.25", content)
        self.assertNotIn("Früh", content)  # unpublished shift is excluded entirely

    def test_internal_full_profile_keeps_wage_and_unpublished_shifts(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse", hourly_wage=18.25)
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        options = export_options_for_profile(ExportPrivacyProfile.INTERNAL_FULL)
        with tempfile.TemporaryDirectory() as directory:
            content = service.export_schedule(
                Path(directory) / "internal.csv", ExportFormat.CSV, options=options
            ).read_text(encoding="utf-8")

        self.assertIn("Eva Retail", content)
        self.assertIn("18.25", content)
        self.assertIn("Früh", content)

    def test_all_privacy_profiles_have_a_label(self) -> None:
        for profile in ExportPrivacyProfile:
            self.assertIn(profile, EXPORT_PRIVACY_PROFILE_LABELS)
            self.assertTrue(EXPORT_PRIVACY_PROFILE_LABELS[profile])

    def test_export_calendar_ics_contains_a_valid_event_for_each_shift(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 5, 8), datetime(2026, 1, 5, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        with tempfile.TemporaryDirectory() as directory:
            output = service.export_calendar_ics(
                Path(directory) / "plan.ics", datetime(2026, 1, 1), datetime(2026, 1, 8)
            )
            content = output.read_bytes().decode("utf-8")

        self.assertTrue(content.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(content.rstrip("\r\n").endswith("END:VCALENDAR"))
        self.assertIn("BEGIN:VEVENT\r\n", content)
        self.assertIn("DTSTART:20260105T080000\r\n", content)
        self.assertIn("DTEND:20260105T160000\r\n", content)
        self.assertIn("Eva Retail", content)

    def test_export_calendar_ics_rejects_end_before_start(self) -> None:
        service = SchedulerService()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                service.export_calendar_ics(Path(directory) / "plan.ics", datetime(2026, 1, 8), datetime(2026, 1, 1))

    def test_export_calendar_ics_filters_by_employee_and_anonymizes_names(self) -> None:
        service = SchedulerService()
        eva = service.add_employee("Eva Retail", "Kasse", "Kasse")
        tom = service.add_employee("Tom Sales", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 5, 8), datetime(2026, 1, 5, 16), 2, "Kasse")
        service.assign(eva.id, shift.id)
        service.assign(tom.id, shift.id)

        with tempfile.TemporaryDirectory() as directory:
            eva_only = service.export_calendar_ics(
                Path(directory) / "eva.ics", datetime(2026, 1, 1), datetime(2026, 1, 8), employee_id=eva.id
            ).read_bytes().decode("utf-8")
            anonymized = service.export_calendar_ics(
                Path(directory) / "anon.ics",
                datetime(2026, 1, 1),
                datetime(2026, 1, 8),
                options=export_options_for_profile(ExportPrivacyProfile.CONTROLLING_ANONYMIZED),
            ).read_bytes().decode("utf-8")

        self.assertEqual(1, eva_only.count("BEGIN:VEVENT"))
        self.assertNotIn("Eva Retail", anonymized)
        self.assertNotIn("Tom Sales", anonymized)
        self.assertIn("Mitarbeiter 1", anonymized.replace("\r\n ", ""))

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                service.export_calendar_ics(
                    Path(directory) / "missing.ics",
                    datetime(2026, 1, 1),
                    datetime(2026, 1, 8),
                    employee_id="does-not-exist",
                )


class RepositoryTests(unittest.TestCase):
    def test_saves_and_loads_service_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "test.sqlite3")
            service = SchedulerService()
            employee = service.add_employee("Eva Retail", "Kasse", "Kasse", break_minutes_per_shift=30)
            employee.absences.append(Absence(datetime(2026, 1, 2, 8), datetime(2026, 1, 2, 16), "Urlaub"))
            shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
            service.add_department("Non-Food")
            service.assign(employee.id, shift.id)
            service.publish_week(datetime(2025, 12, 29), "Repository-Test")
            repository.save(service)

            loaded = repository.load()

        self.assertEqual(1, len(loaded.employees))
        self.assertEqual(1, len(loaded.shifts))
        self.assertEqual([loaded.shifts[0]], loaded.employees[0].shifts)
        self.assertEqual("Urlaub", loaded.employees[0].absences[0].reason)
        self.assertIsNotNone(loaded.shifts[0].published_at)
        self.assertEqual("Repository-Test", loaded.shifts[0].published_by)
        self.assertEqual(30, loaded.employees[0].break_minutes_per_shift)
        self.assertIn("Non-Food", loaded.department_options())

    def test_backup_and_restore_preserves_core_application_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            database_path = directory_path / "dienstplaner.sqlite3"
            backup_path = directory_path / "backup.sqlite3"
            repository = SQLiteSchedulerRepository(database_path)
            service = SchedulerService()
            employee = service.add_employee("Eva Retail", "Kasse", "Kasse", user_id="admin")
            shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse", user_id="admin")
            service.assign(employee.id, shift.id, user_id="planner")
            service.add_absence(employee.id, datetime(2026, 1, 2, 8), datetime(2026, 1, 2, 16), "Urlaub", user_id="planner")
            repository.create_user("admin", "sicheres-passwort", UserRole.ADMIN, "Admin")
            repository.save(service)

            created_backup = repository.backup_to(backup_path)
            self.assertEqual(backup_path, created_backup)

            changed_service = SchedulerService()
            changed_service.add_employee("Max Mutation", "Lager", "Lager", user_id="admin")
            repository.save(changed_service)
            repository.create_user("viewer", "sicheres-passwort", UserRole.VIEWER, "Viewer")

            repository.restore_from(backup_path)
            restored = repository.load()
            authenticated_admin = repository.authenticate_user("admin", "sicheres-passwort")
            authenticated_viewer = repository.authenticate_user("viewer", "sicheres-passwort")
            actions = {event.action for event in repository.list_audit_events(20)}

        self.assertEqual(["Eva Retail"], [item.name for item in restored.employees])
        self.assertEqual(["Früh"], [item.name for item in restored.shifts])
        self.assertEqual([restored.shifts[0]], restored.employees[0].shifts)
        self.assertEqual("Urlaub", restored.employees[0].absences[0].reason)
        self.assertIsNotNone(authenticated_admin)
        self.assertIsNone(authenticated_viewer)
        self.assertIn("employee.created", actions)
        self.assertIn("shift.created", actions)
        self.assertIn("assignment.created", actions)
        self.assertIn("absence.created", actions)

    def test_restore_rejects_non_dienstplaner_sqlite_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            repository = SQLiteSchedulerRepository(directory_path / "dienstplaner.sqlite3")
            invalid_backup = directory_path / "invalid.sqlite3"
            with sqlite3.connect(invalid_backup) as connection:
                connection.execute("CREATE TABLE unrelated(id INTEGER PRIMARY KEY)")

            with self.assertRaisesRegex(ValueError, "gültiges Dienstplaner-Backup"):
                repository.restore_from(invalid_backup)

    def test_saves_and_loads_rule_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "profiles.sqlite3")
            service = SchedulerService()
            service.add_rule_profile(RuleProfile(name="Gastro", min_rest_hours=10, max_daily_hours=9, daily_hours_limit_is_hard=False, is_active=True))

            repository.save(service)
            loaded = repository.load()

        self.assertEqual("Gastro", loaded.active_rule_profile.name)
        self.assertEqual(10, loaded.active_rule_profile.min_rest_hours)
        self.assertFalse(loaded.active_rule_profile.daily_hours_limit_is_hard)
        self.assertEqual("Gastro", loaded.rules.profile.name)

    def test_migrates_legacy_rule_profile_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "legacy_profiles.sqlite3"
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE rule_profiles(
                        id TEXT,
                        name TEXT,
                        min_rest_hours REAL,
                        max_daily_hours REAL,
                        daily_hours_limit_is_hard INTEGER,
                        is_active INTEGER
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO rule_profiles(
                        id, name, min_rest_hours, max_daily_hours,
                        daily_hours_limit_is_hard, is_active
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    ("legacy-strict", "Altprofil", 10, 9, 0, 1),
                )

            repository = SQLiteSchedulerRepository(database_path)
            loaded = repository.load()
            repository.save(loaded)
            reloaded = repository.load()

        self.assertEqual("Altprofil", reloaded.active_rule_profile.name)
        self.assertEqual(10, reloaded.active_rule_profile.min_rest_hours)
        self.assertEqual(9, reloaded.active_rule_profile.max_daily_hours)
        self.assertFalse(reloaded.active_rule_profile.daily_hours_limit_is_hard)
        self.assertTrue(reloaded.active_rule_profile.rest_time_is_hard)
        self.assertEqual(30, reloaded.active_rule_profile.break_after_six_hours_minutes)


class ForecastImportTests(unittest.TestCase):
    def test_imports_semicolon_separated_forecast_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forecast.csv"
            path.write_text("FilialeId;Filiale;Datum;Umsatz;Kunden\n1;Zentrale;01.01.2026;1.234,50;120\n", encoding="utf-8")

            forecasts = ForecastImportService().import_csv(path)

        self.assertEqual(1, len(forecasts))
        self.assertEqual(1234.50, forecasts[0].expected_revenue)
        self.assertEqual(120, forecasts[0].expected_customers)

    def test_import_report_lists_row_field_message_and_severity_for_bad_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forecast.csv"
            path.write_text(
                "FilialeId;Filiale;Datum;Umsatz;Kunden\n"
                "1;Zentrale;01.01.2026;1.234,50;120\n"
                "abc;Nord;01.01.2026;500,00;80\n"
                "2;;01.01.2026;500,00;80\n"
                "3;Süd;nicht-ein-datum;500,00;80\n"
                "4;West;01.01.2026;500,00;nicht-eine-zahl\n"
                "5;Ost\n",
                encoding="utf-8",
            )

            report = ForecastImportService().import_csv_with_report(path)

        self.assertEqual(6, report.total_rows)
        self.assertEqual(1, report.imported_count)
        self.assertEqual(5, report.error_count)

        issues_by_row = {issue.row_number: issue for issue in report.issues}
        self.assertEqual("FilialeId", issues_by_row[3].field)
        self.assertEqual("Fehler", issues_by_row[3].severity)
        self.assertEqual("Filiale", issues_by_row[4].field)
        self.assertEqual("Datum", issues_by_row[5].field)
        self.assertEqual("Kunden", issues_by_row[6].field)
        self.assertEqual("Zeile", issues_by_row[7].field)

    def test_import_csv_still_raises_when_every_row_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forecast.csv"
            path.write_text("FilialeId;Filiale;Datum;Umsatz;Kunden\nabc;Nord;01.01.2026;500,00;80\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                ForecastImportService().import_csv(path)

            report = ForecastImportService().import_csv_with_report(path)
            self.assertEqual(0, report.imported_count)
            self.assertEqual(1, report.error_count)


class EmployeeAndAbsenceWorkflowTests(unittest.TestCase):
    def test_updates_employee_name_in_existing_assignments(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        service.update_employee(employee.id, "Eva Neu", "Kasse", "Kasse", 40, "Zentrale", 16.0, True)

        self.assertEqual(["Eva Neu"], shift.employee_names)

    def test_add_absence_rejects_existing_shift_overlap(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        with self.assertRaises(ValueError):
            service.add_absence(employee.id, datetime(2026, 1, 1, 12), datetime(2026, 1, 1, 18), "Urlaub")

    def test_delete_employee_removes_assignments_from_shifts(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        self.assertTrue(service.delete_employee(employee.id))

        self.assertEqual([], shift.employee_ids)
        self.assertEqual([], shift.employee_names)


class LicenseManagerTests(unittest.TestCase):
    def _signed_license(self, path: Path, *, valid_until, company_name: str = "Muster GmbH", max_users: int = 10):
        from python_dienstplaner.licensing import LicenseManager
        from python_dienstplaner.models import LicenseInfo

        public_key = (TEST_LICENSE_RSA_MODULUS, TEST_LICENSE_RSA_PUBLIC_EXPONENT)
        private_key = (TEST_LICENSE_RSA_MODULUS, TEST_LICENSE_RSA_PRIVATE_EXPONENT)
        manager = LicenseManager(path, public_key=public_key, private_key=private_key)
        license_info = LicenseInfo(
            company_name=company_name,
            license_id="LIC-2026-001",
            valid_until=valid_until,
            max_users=max_users,
            features=["dienstplan", "berichte"],
        )
        signed = LicenseInfo(
            company_name=license_info.company_name,
            license_id=license_info.license_id,
            valid_until=license_info.valid_until,
            max_users=license_info.max_users,
            features=license_info.features,
            signature=manager.sign(license_info),
        )
        manager.save(signed)
        return manager

    def test_accepts_valid_license(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "license.json"
            manager = self._signed_license(path, valid_until=date(2026, 12, 31), company_name="Retail AG")

            result = manager.check(current_user_count=3, today=date(2026, 6, 8))

        self.assertTrue(result.valid)
        self.assertEqual("Retail AG", result.company_name)
        self.assertEqual("Lizenz gültig.", result.message)

    def test_rejects_expired_license(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "license.json"
            manager = self._signed_license(path, valid_until=date(2026, 1, 31))

            result = manager.check(today=date(2026, 6, 8))

        self.assertFalse(result.valid)
        self.assertIn("abgelaufen", result.message)

    def test_rejects_tampered_license_fields(self) -> None:
        import json
        from datetime import date

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "license.json"
            manager = self._signed_license(path, valid_until=date(2026, 12, 31), max_users=5)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["max_users"] = 500
            path.write_text(json.dumps(data), encoding="utf-8")

            result = manager.check(today=date(2026, 6, 8))

        self.assertFalse(result.valid)
        self.assertIn("signatur", result.message.lower())

    def test_reports_missing_license(self) -> None:
        from datetime import date
        from python_dienstplaner.licensing import LicenseManager

        with tempfile.TemporaryDirectory() as directory:
            manager = LicenseManager(Path(directory) / "missing-license.json")

            result = manager.check(today=date(2026, 6, 8))

        self.assertFalse(result.valid)
        self.assertIn("fehlt", result.message)


class DashboardStartupTests(unittest.TestCase):

    def test_scheduler_app_defaults_to_current_calendar_week(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        reference = datetime(2026, 6, 10, 15, 30)

        self.assertEqual(datetime(2026, 6, 8), SchedulerApp._week_start_for_date(reference))

    def test_scheduler_app_uses_german_date_format_helpers(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        reference = datetime(2026, 3, 2, 8, 5)

        self.assertEqual("02.03.2026 08:05", SchedulerApp._format_datetime(reference))
        self.assertEqual("2. Mär", SchedulerApp._format_day_month(reference))
        self.assertEqual("Montag", SchedulerApp._weekday_name(reference))
        self.assertEqual(reference, SchedulerApp._parse_datetime("02.03.2026 08:05"))

    def test_scheduler_app_no_longer_bootstraps_demo_data(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        self.assertFalse(hasattr(SchedulerApp, "_ensure_demo_data"))

    def test_create_app_checks_license_against_active_users_not_employees(self) -> None:
        from python_dienstplaner.app import create_app
        from python_dienstplaner.licensing import LicenseCheckResult

        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "app.sqlite3"
            repository = SQLiteSchedulerRepository(database_path)
            service = SchedulerService()
            service.add_employee("Aktive Mitarbeiterin", "Kasse", "Kasse", is_active=True)
            service.add_employee("Noch eine aktive Mitarbeiterin", "Kasse", "Kasse", is_active=True)
            repository.save(service)
            inactive_user = repository.create_user("inactive", "sicheres-passwort", UserRole.VIEWER)
            repository.create_user("active", "sicheres-passwort", UserRole.PLANNER)
            with sqlite3.connect(database_path) as connection:
                connection.execute("UPDATE users SET is_active = 0 WHERE id = ?", (inactive_user.id,))

            license_result = LicenseCheckResult(True, "Lizenz gültig.")
            with patch("python_dienstplaner.app.LicenseManager") as manager_cls, patch("python_dienstplaner.app.SchedulerApp") as app_cls:
                manager_cls.return_value.check.return_value = license_result

                create_app(database_path, Path(directory) / "license.json")

        manager_cls.return_value.check.assert_called_once_with(current_user_count=1)
        app_cls.assert_called_once()

    def test_legend_only_contains_existing_week_entries(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        service.add_shift("Frühschicht", "Kasse", datetime(2026, 1, 1, 6), datetime(2026, 1, 1, 14), 2, "Kasse")
        employee.absences.append(Absence(datetime(2026, 1, 2, 8), datetime(2026, 1, 2, 16), "Urlaub"))

        items = SchedulerApp._legend_items_for_state(service.shifts, employee.absences)

        self.assertEqual(
            [
                ("#12713A", "Frühschicht\n06:00 – 14:00"),
                ("#F87171", "Abwesend\nEingetragen"),
                ("#CBD5E1", "Offene Schicht\nNicht besetzt"),
            ],
            items,
        )

    def test_legend_returns_no_defaults_without_entries(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        self.assertEqual([], SchedulerApp._legend_items_for_state([], []))

    def test_legend_marks_unassigned_employees_when_requested(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        self.assertIn(
            ("#92400E", "Ohne Schicht\n2 Mitarbeitende"),
            SchedulerApp._legend_items_for_state([], [], unassigned_employees=2),
        )

    def test_employee_week_assignment_helpers_mark_missing_week_shift(self) -> None:
        from python_dienstplaner.app import SchedulerApp
        from python_dienstplaner.models import Employee, Shift

        employee = Employee("Eva Retail", "Kasse", "Kasse")
        week_start = datetime(2026, 1, 5)

        self.assertTrue(SchedulerApp._is_unassigned_for_week(employee, week_start))
        self.assertEqual("Keine Schicht diese Woche", SchedulerApp._employee_week_assignment_text([]))

        shift = Shift("Früh", "Kasse", datetime(2026, 1, 5, 8), datetime(2026, 1, 5, 16), 1, "Kasse")
        employee.shifts.append(shift)

        self.assertFalse(SchedulerApp._is_unassigned_for_week(employee, week_start))
        self.assertEqual([shift], SchedulerApp._employee_week_shifts(employee, week_start))
        self.assertEqual("Früh Mo 08:00", SchedulerApp._employee_week_assignment_text([shift]))


class UiActionHelperTests(unittest.TestCase):
    def test_redact_log_value_removes_sensitive_terms_and_bounds_length(self) -> None:
        from python_dienstplaner.app import redact_log_value

        value = "Passwort=geheim Recovery-Code: ABC-123 Token=secret " + ("x" * 400)

        redacted = redact_log_value(value, max_length=80)

        self.assertNotIn("geheim", redacted)
        self.assertNotIn("ABC-123", redacted)
        self.assertNotIn("secret", redacted.lower())
        self.assertLessEqual(len(redacted), 81)
        self.assertTrue(redacted.endswith("…"))

    def test_configure_app_logging_writes_to_given_directory_once(self) -> None:
        from python_dienstplaner.app import configure_app_logging

        with tempfile.TemporaryDirectory() as directory:
            logger = configure_app_logging(Path(directory))
            handler_count = len([handler for handler in logger.handlers if getattr(handler, "_dienstplaner_file_handler", False)])

            same_logger = configure_app_logging(Path(directory))
            same_handler_count = len([handler for handler in same_logger.handlers if getattr(handler, "_dienstplaner_file_handler", False)])
            logger.info("ui_action=test event=completed detail=ok")

            for handler in logger.handlers:
                handler.flush()

            self.assertIs(logger, same_logger)
            self.assertEqual(handler_count, same_handler_count)
            self.assertTrue((Path(directory) / "dienstplaner.log").exists())

    def test_run_ui_action_handles_expected_domain_error(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        app = SchedulerApp.__new__(SchedulerApp)
        statuses: list[str] = []
        app._set_status = statuses.append
        app._log_ui_info = lambda *_args, **_kwargs: None
        app._log_ui_failure = lambda *_args, **_kwargs: None

        with patch("python_dienstplaner.app.messagebox.showwarning") as showwarning:
            app._run_ui_action("Dienstplan veröffentlichen", lambda: (_ for _ in ()).throw(ValueError("Offene Slots vorhanden")))

        self.assertEqual("Dienstplan veröffentlichen läuft …", statuses[0])
        self.assertEqual("Dienstplan veröffentlichen nicht möglich: Offene Slots vorhanden", statuses[-1])
        showwarning.assert_called_once()

    def test_run_ui_action_logs_technical_error_without_raw_message_in_dialog(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        app = SchedulerApp.__new__(SchedulerApp)
        statuses: list[str] = []
        failures: list[tuple[str, BaseException]] = []
        app._set_status = statuses.append
        app._log_ui_info = lambda *_args, **_kwargs: None
        app._log_ui_failure = lambda action, exc: failures.append((action, exc))

        with patch("python_dienstplaner.app.messagebox.showerror") as showerror:
            app._run_ui_action("Export", lambda: (_ for _ in ()).throw(OSError("/tmp/eva_export.csv nicht beschreibbar")))

        self.assertEqual("Export fehlgeschlagen. Details stehen im lokalen Logfile.", statuses[-1])
        self.assertEqual("Export", failures[0][0])
        self.assertIsInstance(failures[0][1], OSError)
        self.assertNotIn("eva_export", showerror.call_args.args[1])


class SchedulerAppPersistenceTests(unittest.TestCase):
    def test_persist_changes_saves_service_and_updates_status(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        class RepositoryStub:
            def __init__(self) -> None:
                self.saved_service = None

            def save(self, service: SchedulerService) -> None:
                self.saved_service = service

        service = SchedulerService()
        repository = RepositoryStub()
        app = SchedulerApp.__new__(SchedulerApp)
        app.service = service
        app.repository = repository
        statuses: list[str] = []
        app._set_status = statuses.append

        self.assertTrue(app._persist_changes("Automatisch gespeichert."))

        self.assertIs(repository.saved_service, service)
        self.assertEqual(["Automatisch gespeichert."], statuses)

    def test_persist_changes_reports_sqlite_write_errors(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        class FailingRepositoryStub:
            def save(self, service: SchedulerService) -> None:
                raise sqlite3.OperationalError("database is locked")

        app = SchedulerApp.__new__(SchedulerApp)
        app.service = SchedulerService()
        app.repository = FailingRepositoryStub()
        statuses: list[str] = []
        app._set_status = statuses.append

        with patch("python_dienstplaner.app.messagebox.showerror") as showerror:
            self.assertFalse(app._persist_changes("Automatisch gespeichert."))

        self.assertEqual(["Speichern fehlgeschlagen – Änderungen sind nur bis zum Beenden im Speicher."], statuses)
        showerror.assert_called_once()


class PublishingAndForecastTests(unittest.TestCase):
    def test_publish_week_persists_status(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        count = service.publish_week(datetime(2025, 12, 29), "Tester")

        self.assertEqual(1, count)
        self.assertIsNotNone(shift.published_at)
        self.assertEqual("Tester", shift.published_by)

    def test_publish_week_rejects_open_slots(self) -> None:
        service = SchedulerService()
        service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        with self.assertRaises(ValueError):
            service.publish_week(datetime(2025, 12, 29), "Tester")

    def test_forecasts_are_saved_loaded_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "test.sqlite3")
            service = SchedulerService()
            forecasts = ForecastImportService().import_csv(_write_forecast(Path(directory) / "forecast.csv"))
            service.add_forecasts(forecasts)
            repository.save(service)

            loaded = repository.load()

        self.assertEqual(1, len(loaded.forecasts))
        self.assertIn("Forecast", [metric.category for metric in loaded.create_reports()])


    def test_new_database_records_latest_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "new.sqlite3"
            SQLiteSchedulerRepository(database_path)

            with sqlite3.connect(database_path) as connection:
                version = connection.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()[0]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

        self.assertEqual(SCHEMA_VERSION, version)
        self.assertIn("schema_version", tables)
        self.assertIn("forecasts", tables)

    def test_migrates_legacy_schema_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "legacy.sqlite3"
            employee_id = "employee-1"
            shift_id = "shift-1"
            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE employees(
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        department TEXT NOT NULL,
                        qualification TEXT NOT NULL,
                        weekly_hours_limit INTEGER NOT NULL,
                        branch TEXT NOT NULL,
                        hourly_wage REAL NOT NULL,
                        is_active INTEGER NOT NULL
                    );
                    CREATE TABLE shifts(
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        department TEXT NOT NULL,
                        start TEXT NOT NULL,
                        end TEXT NOT NULL,
                        required_employees INTEGER NOT NULL,
                        required_qualification TEXT NOT NULL,
                        branch TEXT NOT NULL
                    );
                    CREATE TABLE assignments(
                        employee_id TEXT NOT NULL,
                        shift_id TEXT NOT NULL,
                        PRIMARY KEY(employee_id, shift_id)
                    );
                    CREATE TABLE absences(
                        employee_id TEXT NOT NULL,
                        start TEXT NOT NULL,
                        end TEXT NOT NULL,
                        reason TEXT NOT NULL DEFAULT ''
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO employees VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (employee_id, "Eva Legacy", "Kasse", "Kasse", 40, "Zentrale", 13.5, 1),
                )
                connection.execute(
                    "INSERT INTO shifts VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (shift_id, "Früh", "Kasse", "2026-01-01T08:00:00", "2026-01-01T16:00:00", 1, "Kasse", "Zentrale"),
                )
                connection.execute("INSERT INTO assignments VALUES(?, ?)", (employee_id, shift_id))
                connection.execute(
                    "INSERT INTO absences(employee_id, start, end, reason) VALUES(?, ?, ?, ?)",
                    (employee_id, "2026-01-02T08:00:00", "2026-01-02T16:00:00", "Urlaub"),
                )

            repository = SQLiteSchedulerRepository(database_path)
            first_load = repository.load()
            SQLiteSchedulerRepository(database_path)
            second_load = repository.load()

            with sqlite3.connect(database_path) as connection:
                version = connection.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()[0]
                employee_columns = {row[1] for row in connection.execute("PRAGMA table_info(employees)")}
                shift_columns = {row[1] for row in connection.execute("PRAGMA table_info(shifts)")}
                absence_ids = [row[0] for row in connection.execute("SELECT id FROM absences")]

        self.assertEqual(SCHEMA_VERSION, version)
        self.assertIn("break_minutes_per_shift", employee_columns)
        self.assertIn("published_at", shift_columns)
        self.assertIn("published_by", shift_columns)
        self.assertTrue(all(absence_ids))
        self.assertEqual(1, len(first_load.employees))
        self.assertEqual([first_load.shifts[0]], first_load.employees[0].shifts)
        self.assertEqual(1, len(second_load.employees))
        self.assertEqual("Eva Legacy", second_load.employees[0].name)

    def test_exports_reports_as_csv(self) -> None:
        service = SchedulerService()

        with tempfile.TemporaryDirectory() as directory:
            output = service.export_reports(Path(directory) / "berichte.csv")
            content = output.read_text(encoding="utf-8")

        self.assertIn("Kategorie;Kennzahl;Wert;Hinweis", content)

class UserAuthenticationTests(unittest.TestCase):
    def test_create_user_hashes_password_with_unique_salt_and_authenticates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")

            user = repository.create_user("admin", "sicheres-passwort", "admin", "Admin")
            authenticated = repository.authenticate_user("ADMIN", "sicheres-passwort")

            self.assertEqual(1, repository.user_count())
            self.assertIsNotNone(authenticated)
            self.assertEqual(user.id, authenticated.id)
            self.assertNotEqual("sicheres-passwort", user.password_hash)
            self.assertRegex(user.password_salt, r"^[0-9a-f]{32}$")
            self.assertRegex(user.password_hash, r"^[0-9a-f]{64}$")
            self.assertIsNone(repository.authenticate_user("admin", "falsch"))

    def test_active_user_count_ignores_inactive_users_and_employees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "auth.sqlite3"
            repository = SQLiteSchedulerRepository(database_path)
            service = SchedulerService()
            service.add_employee("Aktive Mitarbeiterin", "Kasse", "Kasse", is_active=True)
            service.add_employee("Inaktiver Mitarbeiter", "Lager", "Lager", is_active=False)
            repository.save(service)
            active_user = repository.create_user("active", "sicheres-passwort", UserRole.PLANNER)
            inactive_user = repository.create_user("inactive", "sicheres-passwort", UserRole.VIEWER)

            with sqlite3.connect(database_path) as connection:
                connection.execute("UPDATE users SET is_active = 0 WHERE id = ?", (inactive_user.id,))

            self.assertEqual(2, repository.user_count())
            self.assertEqual(1, repository.active_user_count())
            self.assertEqual(active_user.id, repository.authenticate_user("active", "sicheres-passwort").id)
            self.assertIsNone(repository.authenticate_user("inactive", "sicheres-passwort"))

    def test_password_salts_are_unique_per_user(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")

            first = repository.create_user("first", "gleiches-passwort", UserRole.ADMIN)
            second = repository.create_user("second", "gleiches-passwort", UserRole.PLANNER)

            self.assertNotEqual(first.password_salt, second.password_salt)
            self.assertNotEqual(first.password_hash, second.password_hash)

    def test_rejects_short_passwords_and_duplicate_usernames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            repository.create_user("admin", "sicheres-passwort", UserRole.ADMIN)

            with self.assertRaises(ValueError):
                repository.create_user("admin", "anderes-passwort", UserRole.ADMIN)
            with self.assertRaises(ValueError):
                repository.create_user("viewer", "kurz", UserRole.VIEWER)

    def test_rejects_empty_trivial_and_single_group_passwords(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")

            invalid_passwords = ["            ", "password", "admin123", "12345678", "aaaaaaaaaaaa"]
            for password in invalid_passwords:
                with self.subTest(password=password):
                    with self.assertRaises(ValueError):
                        repository.create_user(f"user-{len(password)}-{ord(password[0])}", password, UserRole.ADMIN)

    def test_accepts_valid_passwords_for_user_creation_and_admin_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")

            user = repository.create_user("admin", "Sicheres Passwort 2026", UserRole.ADMIN)
            recovery_code = repository.create_admin_recovery_code()
            recovered_user, _next_code = repository.reset_admin_with_recovery_code(
                recovery_code,
                "admin-neu",
                "Noch sicherer 2026!",
            )

            self.assertEqual(UserRole.ADMIN, user.role)
            self.assertEqual(UserRole.ADMIN, recovered_user.role)

    def test_admin_recovery_code_creates_new_admin_and_rotates_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "auth.sqlite3"
            repository = SQLiteSchedulerRepository(database_path)
            repository.create_user("admin", "sicheres-passwort", UserRole.ADMIN)

            recovery_code = repository.create_admin_recovery_code()
            self.assertTrue(repository.has_admin_recovery_code())

            with sqlite3.connect(database_path) as connection:
                stored_hash, stored_salt = connection.execute(
                    "SELECT code_hash, code_salt FROM auth_recovery WHERE id = 'admin_recovery'"
                ).fetchone()
            self.assertNotEqual(recovery_code, stored_hash)
            self.assertRegex(stored_salt, r"^[0-9a-f]{32}$")
            self.assertRegex(stored_hash, r"^[0-9a-f]{64}$")

            recovered_admin, next_recovery_code = repository.reset_admin_with_recovery_code(
                recovery_code,
                "admin-neu",
                "neues-sicheres-passwort",
                "Neuer Admin",
            )

            self.assertEqual(UserRole.ADMIN, recovered_admin.role)
            self.assertEqual(recovered_admin.id, repository.authenticate_user("admin-neu", "neues-sicheres-passwort").id)
            self.assertNotEqual(recovery_code, next_recovery_code)
            with self.assertRaises(ValueError):
                repository.reset_admin_with_recovery_code(recovery_code, "admin-alt", "anderes-passwort")

    def test_admin_recovery_requires_existing_valid_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            repository.create_user("admin", "sicheres-passwort", UserRole.ADMIN)

            with self.assertRaises(ValueError):
                repository.reset_admin_with_recovery_code("irgendein-code", "admin-neu", "neues-passwort")

            recovery_code = repository.create_admin_recovery_code()
            with self.assertRaises(ValueError):
                repository.reset_admin_with_recovery_code("falscher-code", "admin-neu", "neues-passwort")
            self.assertIsNone(repository.authenticate_user("admin-neu", "neues-passwort"))
            self.assertTrue(recovery_code)


class UserManagementTests(unittest.TestCase):
    def test_get_user_returns_none_for_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            self.assertIsNone(repository.get_user("does-not-exist"))

    def test_set_user_active_toggles_login_ability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            admin = repository.create_user("admin", "Sicheres Passwort 2026", UserRole.ADMIN)
            planner = repository.create_user("planer", "Sicheres Passwort 2026", UserRole.PLANNER)

            repository.set_user_active(planner.id, False, user_id=admin.id)

            self.assertFalse(repository.get_user(planner.id).is_active)
            self.assertIsNone(repository.authenticate_user("planer", "Sicheres Passwort 2026"))

            repository.set_user_active(planner.id, True, user_id=admin.id)

            self.assertTrue(repository.get_user(planner.id).is_active)
            self.assertIsNotNone(repository.authenticate_user("planer", "Sicheres Passwort 2026"))

    def test_set_user_active_refuses_to_deactivate_last_active_admin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            admin = repository.create_user("admin", "Sicheres Passwort 2026", UserRole.ADMIN)

            with self.assertRaises(ValueError):
                repository.set_user_active(admin.id, False)
            self.assertTrue(repository.get_user(admin.id).is_active)

    def test_set_user_active_allows_deactivating_admin_when_another_admin_remains(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            first_admin = repository.create_user("admin1", "Sicheres Passwort 2026", UserRole.ADMIN)
            second_admin = repository.create_user("admin2", "Sicheres Passwort 2026", UserRole.ADMIN)

            repository.set_user_active(first_admin.id, False, user_id=second_admin.id)

            self.assertFalse(repository.get_user(first_admin.id).is_active)

    def test_update_user_role_changes_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            admin = repository.create_user("admin", "Sicheres Passwort 2026", UserRole.ADMIN)
            planner = repository.create_user("planer", "Sicheres Passwort 2026", UserRole.PLANNER)

            updated = repository.update_user_role(planner.id, UserRole.VIEWER, user_id=admin.id)

            self.assertEqual(UserRole.VIEWER, updated.role)
            self.assertEqual(UserRole.VIEWER, repository.get_user(planner.id).role)

    def test_update_user_role_refuses_to_demote_last_active_admin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            admin = repository.create_user("admin", "Sicheres Passwort 2026", UserRole.ADMIN)

            with self.assertRaises(ValueError):
                repository.update_user_role(admin.id, UserRole.PLANNER)
            self.assertEqual(UserRole.ADMIN, repository.get_user(admin.id).role)

    def test_admin_reset_password_replaces_hash_and_enforces_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            admin = repository.create_user("admin", "Sicheres Passwort 2026", UserRole.ADMIN)
            planner = repository.create_user("planer", "Sicheres Passwort 2026", UserRole.PLANNER)

            repository.admin_reset_password(planner.id, "Neues Sicheres Passwort!", user_id=admin.id)

            self.assertIsNone(repository.authenticate_user("planer", "Sicheres Passwort 2026"))
            self.assertIsNotNone(repository.authenticate_user("planer", "Neues Sicheres Passwort!"))
            with self.assertRaises(ValueError):
                repository.admin_reset_password(planner.id, "kurz")

    def test_user_management_actions_are_recorded_in_audit_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "auth.sqlite3")
            admin = repository.create_user("admin", "Sicheres Passwort 2026", UserRole.ADMIN, user_id="system")
            planner = repository.create_user("planer", "Sicheres Passwort 2026", UserRole.PLANNER, user_id=admin.id)
            repository.set_user_active(planner.id, False, user_id=admin.id)
            repository.update_user_role(planner.id, UserRole.VIEWER, user_id=admin.id)
            repository.admin_reset_password(planner.id, "Noch sicherer 2026!", user_id=admin.id)

            events = repository.list_audit_events(50)
            actions = [event.action for event in reversed(events)]
            self.assertEqual(
                ["user.created", "user.created", "user.deactivated", "user.role_changed", "user.password_reset"],
                actions,
            )
            for event in events:
                self.assertNotIn("Sicheres Passwort", event.before)
                self.assertNotIn("Sicheres Passwort", event.after)

            integrity = repository.verify_audit_integrity()
            self.assertTrue(integrity.is_valid, integrity.problems)


class RolePermissionTests(unittest.TestCase):
    def test_role_permissions_match_locked_actions(self) -> None:
        admin = User("admin", UserRole.ADMIN)
        planner = User("planer", UserRole.PLANNER)
        viewer = User("viewer", UserRole.VIEWER)

        self.assertTrue(admin.has_permission(Permission.MANAGE_EMPLOYEES))
        self.assertTrue(admin.has_permission(Permission.MANAGE_ABSENCES))
        self.assertTrue(admin.has_permission(Permission.PUBLISH_SCHEDULE))
        self.assertTrue(admin.has_permission(Permission.EXPORT))
        self.assertTrue(admin.has_permission(Permission.MANAGE_USERS))
        self.assertFalse(planner.has_permission(Permission.MANAGE_EMPLOYEES))
        self.assertTrue(planner.has_permission(Permission.MANAGE_ABSENCES))
        self.assertTrue(planner.has_permission(Permission.PUBLISH_SCHEDULE))
        self.assertTrue(planner.has_permission(Permission.EXPORT))
        self.assertFalse(planner.has_permission(Permission.MANAGE_USERS))
        self.assertFalse(viewer.has_permission(Permission.EXPORT))
        self.assertFalse(viewer.has_permission(Permission.MANAGE_USERS))

    def test_app_permission_helper_blocks_locked_actions_for_viewer(self) -> None:
        from python_dienstplaner.secure_app import AuthenticatedSchedulerApp

        viewer = User("viewer", UserRole.VIEWER)
        planner = User("planer", UserRole.PLANNER)

        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(viewer, Permission.EXPORT))
        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(viewer, Permission.PUBLISH_SCHEDULE))
        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(viewer, Permission.MANAGE_ABSENCES))
        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(viewer, Permission.MANAGE_EMPLOYEES))
        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(viewer, Permission.MANAGE_USERS))
        self.assertTrue(AuthenticatedSchedulerApp._user_has_permission(planner, Permission.EXPORT))
        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(planner, Permission.MANAGE_EMPLOYEES))
        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(planner, Permission.MANAGE_USERS))
        self.assertFalse(AuthenticatedSchedulerApp._user_has_permission(None, Permission.EXPORT))

    def test_scheduler_app_constructor_does_not_force_modal_login_for_tests(self) -> None:
        import inspect
        from python_dienstplaner.secure_app import AuthenticatedSchedulerApp

        scheduler_parameters = inspect.signature(AuthenticatedSchedulerApp).parameters
        self.assertIn("current_user", scheduler_parameters)
        self.assertNotIn("require_authentication", scheduler_parameters)
        self.assertIn("AuthenticatedSchedulerApp", Path("python_dienstplaner/secure_app.py").read_text(encoding="utf-8"))


class AppIntegrityTests(unittest.TestCase):
    def test_scheduler_app_has_no_duplicate_method_definitions(self) -> None:
        import ast
        from collections import Counter

        source = Path("python_dienstplaner/app.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        scheduler = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "SchedulerApp")
        names = [node.name for node in scheduler.body if isinstance(node, ast.FunctionDef)]
        duplicates = [name for name, count in Counter(names).items() if count > 1]

        self.assertEqual([], duplicates)


def _write_forecast(path: Path) -> Path:
    path.write_text("FilialeId;Filiale;Datum;Umsatz;Kunden\n1;Zentrale;01.01.2026;1.234,50;120\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
