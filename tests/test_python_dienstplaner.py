from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

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

    def test_blocks_overlapping_absence(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        employee.absences.append(Absence(datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 12), "Urlaub"))
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

        result = service.assign(employee.id, shift.id)

        self.assertFalse(result.success)
        self.assertIn("Der Mitarbeiter ist im Schichtzeitraum abwesend (Urlaub).", result.errors)

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
            repository.save(service)

            loaded = repository.load()

        self.assertEqual(1, len(loaded.employees))
        self.assertEqual(1, len(loaded.shifts))
        self.assertEqual([loaded.shifts[0]], loaded.employees[0].shifts)
        self.assertEqual("Urlaub", loaded.employees[0].absences[0].reason)


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
    def test_scheduler_app_no_longer_bootstraps_demo_data(self) -> None:
        from python_dienstplaner.app import SchedulerApp

        self.assertFalse(hasattr(SchedulerApp, "_ensure_demo_data"))


if __name__ == "__main__":
    unittest.main()
