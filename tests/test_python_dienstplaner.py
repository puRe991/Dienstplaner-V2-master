from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_dienstplaner.models import Absence, ExportFormat
from python_dienstplaner.repository import SQLiteSchedulerRepository
from python_dienstplaner.services import ForecastImportService, SchedulerService


class SchedulerServiceTests(unittest.TestCase):
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


    def test_unassign_removes_employee_and_shift_links(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        self.assertTrue(service.unassign(employee.id, shift.id))

        self.assertEqual([], employee.shifts)
        self.assertEqual([], shift.employee_ids)
        self.assertEqual([], shift.employee_names)

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
            employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
            employee.absences.append(Absence(datetime(2026, 1, 2, 8), datetime(2026, 1, 2, 16), "Urlaub"))
            shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
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
