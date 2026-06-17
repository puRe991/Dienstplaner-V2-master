from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_dienstplaner.application_service import AuthorizationError, SchedulerApplicationService
from python_dienstplaner.auth import User, UserRole
from python_dienstplaner.models import ExportFormat, RuleProfile
from python_dienstplaner.services import SchedulerService


class SchedulerApplicationServiceAuthorizationTests(unittest.TestCase):
    def test_viewer_direct_calls_are_rejected_for_productive_actions(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)
        app_service = SchedulerApplicationService(service, User("viewer", UserRole.VIEWER, id="viewer-1"))

        with tempfile.TemporaryDirectory() as directory:
            denied_calls = [
                lambda: app_service.add_employee("Max Muster", "Kasse", "Kasse"),
                lambda: app_service.update_employee(employee.id, "Eva Neu", "Kasse", "Kasse"),
                lambda: app_service.delete_employee(employee.id),
                lambda: app_service.add_absence(employee.id, datetime(2026, 1, 2), datetime(2026, 1, 3), "Urlaub"),
                lambda: app_service.delete_absence("missing"),
                lambda: app_service.publish_week(datetime(2025, 12, 29)),
                lambda: app_service.export_schedule(Path(directory) / "plan.csv", ExportFormat.CSV),
                lambda: app_service.export_reports(Path(directory) / "reports.csv"),
                lambda: app_service.add_rule_profile(RuleProfile(name="Gastro")),
                lambda: app_service.update_rule_profile(service.active_rule_profile.id, RuleProfile(name="Neu")),
                lambda: app_service.delete_rule_profile(service.active_rule_profile.id),
            ]
            for call in denied_calls:
                with self.subTest(call=call):
                    with self.assertRaises(AuthorizationError):
                        call()

        self.assertEqual([employee], service.employees)
        self.assertEqual([], employee.absences)
        self.assertIsNone(shift.published_at)
        self.assertEqual(1, len(service.rule_profiles))

    def test_planner_cannot_manage_employees_or_rule_profiles_directly(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        app_service = SchedulerApplicationService(service, User("planner", UserRole.PLANNER, id="planner-1"))

        with self.assertRaises(AuthorizationError):
            app_service.delete_employee(employee.id)
        with self.assertRaises(AuthorizationError):
            app_service.add_rule_profile(RuleProfile(name="Filiale"))

        absence = app_service.add_absence(employee.id, datetime(2026, 1, 2), datetime(2026, 1, 3), "Urlaub")
        self.assertEqual("Urlaub", absence.reason)
        self.assertEqual([employee], service.employees)
        self.assertEqual(1, len(service.rule_profiles))

    def test_admin_mutations_use_current_user_for_audit_context(self) -> None:
        service = SchedulerService()
        app_service = SchedulerApplicationService(service, User("admin", UserRole.ADMIN, id="admin-1", display_name="Admin User"))

        employee = app_service.add_employee("Eva Retail", "Kasse", "Kasse")

        self.assertEqual("Eva Retail", employee.name)
        self.assertEqual("admin-1", service.audit_events[-1].user_id)
        self.assertEqual("employee.created", service.audit_events[-1].action)


if __name__ == "__main__":
    unittest.main()
