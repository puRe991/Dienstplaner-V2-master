from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_dienstplaner.models import DEFAULT_ABSENCE_REASONS, Absence, ExportFormat
from python_dienstplaner.repository import SQLiteSchedulerRepository
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


class ForecastImportTests(unittest.TestCase):
    def test_imports_semicolon_separated_forecast_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forecast.csv"
            path.write_text("FilialeId;Filiale;Datum;Umsatz;Kunden\n1;Zentrale;01.01.2026;1.234,50;120\n", encoding="utf-8")

            forecasts = ForecastImportService().import_csv(path)

        self.assertEqual(1, len(forecasts))
        self.assertEqual(1234.50, forecasts[0].expected_revenue)
        self.assertEqual(120, forecasts[0].expected_customers)



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

    def test_exports_reports_as_csv(self) -> None:
        service = SchedulerService()

        with tempfile.TemporaryDirectory() as directory:
            output = service.export_reports(Path(directory) / "berichte.csv")
            content = output.read_text(encoding="utf-8")

        self.assertIn("Kategorie;Kennzahl;Wert;Hinweis", content)


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
