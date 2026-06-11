from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_dienstplaner.repository import DEFAULT_AUDIT_LOAD_LIMIT, SQLiteSchedulerRepository
from python_dienstplaner.services import SchedulerService


class AuditLoggingTests(unittest.TestCase):
    def test_persists_employee_change_audit_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "test.sqlite3")
            service = SchedulerService()
            employee = service.add_employee("Eva Retail", "Kasse", "Kasse", user_id="admin-1")
            service.update_employee(employee.id, "Eva Neu", "Kasse", "Kasse", 40, "Zentrale", 16.0, True, user_id="admin-1")

            repository.save(service)
            events = repository.list_audit_events()

        update_event = next(event for event in events if event.action == "employee.updated")
        self.assertEqual("admin-1", update_event.user_id)
        self.assertEqual("employee", update_event.entity_type)
        self.assertEqual(employee.id, update_event.entity_id)
        self.assertEqual("Eva Retail", json.loads(update_event.before)["name"])
        self.assertEqual("Eva Neu", json.loads(update_event.after)["name"])

    def test_persists_assignment_audit_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "test.sqlite3")
            service = SchedulerService()
            employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
            shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")

            result = service.assign(employee.id, shift.id, user_id="planner-1")
            repository.save(service)
            events = repository.list_audit_events()

        self.assertTrue(result.success)
        assignment_event = next(event for event in events if event.action == "assignment.created")
        self.assertEqual("planner-1", assignment_event.user_id)
        self.assertEqual("assignment", assignment_event.entity_type)
        self.assertEqual(f"{employee.id}:{shift.id}", assignment_event.entity_id)
        self.assertFalse(json.loads(assignment_event.before)["assigned"])
        self.assertTrue(json.loads(assignment_event.after)["assigned"])

    def test_persists_publication_audit_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "test.sqlite3")
            service = SchedulerService()
            employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
            shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
            service.assign(employee.id, shift.id)

            count = service.publish_week(datetime(2025, 12, 29), "Planerin", user_id="planner-1")
            repository.save(service)
            events = repository.list_audit_events()

        publication_event = next(event for event in events if event.action == "schedule.published")
        self.assertEqual(1, count)
        self.assertEqual("week", publication_event.entity_type)
        self.assertEqual("2025-12-29", publication_event.entity_id)
        self.assertIsNone(json.loads(publication_event.before)[0]["published_at"])
        self.assertIsNotNone(json.loads(publication_event.after)[0]["published_at"])

    def test_load_limits_in_memory_audit_events_without_pruning_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteSchedulerRepository(Path(directory) / "test.sqlite3")
            service = SchedulerService()
            for index in range(DEFAULT_AUDIT_LOAD_LIMIT + 5):
                service.record_audit_event("test.event", "test", str(index), None, {"index": index})
            repository.save(service)

            loaded = repository.load()
            all_events = repository.list_audit_events(DEFAULT_AUDIT_LOAD_LIMIT + 10)

        self.assertEqual(DEFAULT_AUDIT_LOAD_LIMIT, len(loaded.audit_events))
        self.assertEqual(DEFAULT_AUDIT_LOAD_LIMIT + 5, len(all_events))

    def test_audit_event_normalizes_empty_user_id(self) -> None:
        service = SchedulerService()

        event = service.record_audit_event(" test.event ", " test ", 42, None, {"ok": True}, user_id="  ")

        self.assertEqual("system", event.user_id)
        self.assertEqual("test.event", event.action)
        self.assertEqual("test", event.entity_type)
        self.assertEqual("42", event.entity_id)

    def test_deleting_employee_audits_removed_assignment(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        self.assertTrue(service.delete_employee(employee.id, user_id="admin-1"))

        assignment_deletes = [event for event in service.audit_events if event.action == "assignment.deleted"]
        self.assertEqual(1, len(assignment_deletes))
        self.assertEqual(f"{employee.id}:{shift.id}", assignment_deletes[0].entity_id)
        self.assertTrue(json.loads(assignment_deletes[0].before)["assigned"])
        self.assertFalse(json.loads(assignment_deletes[0].after)["assigned"])

    def test_deleting_shift_audits_removed_assignment(self) -> None:
        service = SchedulerService()
        employee = service.add_employee("Eva Retail", "Kasse", "Kasse")
        shift = service.add_shift("Früh", "Kasse", datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 16), 1, "Kasse")
        service.assign(employee.id, shift.id)

        self.assertTrue(service.delete_shift(shift.id, user_id="admin-1"))

        assignment_deletes = [event for event in service.audit_events if event.action == "assignment.deleted"]
        self.assertEqual(1, len(assignment_deletes))
        self.assertEqual(f"{employee.id}:{shift.id}", assignment_deletes[0].entity_id)
        self.assertTrue(json.loads(assignment_deletes[0].before)["assigned"])
        self.assertFalse(json.loads(assignment_deletes[0].after)["assigned"])


if __name__ == "__main__":
    unittest.main()
