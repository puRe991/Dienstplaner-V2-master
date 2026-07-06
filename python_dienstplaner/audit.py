from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from .auth import User
from .models import Absence, AssignmentResult, Employee, ExportFormat, Shift

DEFAULT_AUDIT_LOAD_LIMIT = 500
GENESIS_AUDIT_HASH = ""


@dataclass(frozen=True)
class AuditIntegrityResult:
    """Result of the audit hash-chain verification."""

    is_valid: bool
    checked_events: int
    problems: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit entry storing actor, action, target, JSON snapshots and hash-chain data."""

    timestamp: datetime
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    before: str = ""
    after: str = ""
    previous_hash: str = GENESIS_AUDIT_HASH
    event_hash: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        action = str(self.action).strip()
        entity_type = str(self.entity_type).strip()
        if not action:
            raise ValueError("Audit-Aktion ist erforderlich.")
        if not entity_type:
            raise ValueError("Audit-Entitätstyp ist erforderlich.")
        object.__setattr__(self, "user_id", str(self.user_id or "system").strip() or "system")
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "entity_type", entity_type)
        object.__setattr__(self, "entity_id", str(self.entity_id or "").strip())
        object.__setattr__(self, "before", str(self.before or ""))
        object.__setattr__(self, "after", str(self.after or ""))
        object.__setattr__(self, "previous_hash", str(self.previous_hash or ""))
        object.__setattr__(self, "event_hash", str(self.event_hash or ""))


def calculate_audit_event_hash(
    *,
    previous_hash: str,
    timestamp: datetime,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: str,
    after: str,
) -> str:
    """Return a deterministic SHA-256 hash for an audit event.

    The event id is intentionally not part of the hash because ids are storage
    metadata. The protected payload is exactly the business audit content plus
    the previous link in the chain.
    """

    payload = [
        str(previous_hash or ""),
        timestamp.isoformat(),
        str(user_id or "system"),
        str(action or ""),
        str(entity_type or ""),
        str(entity_id or ""),
        str(before or ""),
        str(after or ""),
    ]
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def audit_json(value: object | None) -> str:
    if value is None:
        return ""
    return json.dumps(json_ready(value), ensure_ascii=False, sort_keys=True)


def json_ready(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_ready(item) for item in value]
    if is_dataclass(value):
        return json_ready(asdict(value))
    return str(value)


def employee_snapshot(employee: Employee) -> dict[str, object]:
    return {
        "id": employee.id,
        "name": employee.name,
        "department": employee.department,
        "qualification": employee.qualification,
        "weekly_hours_limit": employee.weekly_hours_limit,
        "branch": employee.branch,
        "hourly_wage": employee.hourly_wage,
        "is_active": employee.is_active,
        "break_minutes_per_shift": employee.break_minutes_per_shift,
        "shift_ids": [shift.id for shift in employee.shifts],
        "absence_ids": [absence.id for absence in employee.absences],
    }


def shift_snapshot(shift: Shift) -> dict[str, object]:
    return {
        "id": shift.id,
        "name": shift.name,
        "department": shift.department,
        "start": shift.start,
        "end": shift.end,
        "required_employees": shift.required_employees,
        "required_qualification": shift.required_qualification,
        "branch": shift.branch,
        "employee_ids": list(shift.employee_ids),
        "employee_names": list(shift.employee_names),
        "published_at": shift.published_at,
        "published_by": shift.published_by,
    }


def absence_snapshot(absence: Absence, employee_id: str) -> dict[str, object]:
    return {
        "id": absence.id,
        "employee_id": employee_id,
        "start": absence.start,
        "end": absence.end,
        "reason": absence.reason,
    }


def assignment_snapshot(employee: Employee, shift: Shift) -> dict[str, object]:
    employee_has_shift = any(item.id == shift.id for item in employee.shifts)
    shift_has_employee = employee.id in shift.employee_ids
    return {
        "employee_id": employee.id,
        "employee_name": employee.name,
        "shift_id": shift.id,
        "shift_name": shift.name,
        "assigned": employee_has_shift and shift_has_employee,
        "employee_shift_ids": [item.id for item in employee.shifts],
        "shift_employee_ids": list(shift.employee_ids),
    }


def user_snapshot(user: User) -> dict[str, object]:
    """Audit snapshot for a user account. Excludes password hash and salt."""
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
        "is_active": user.is_active,
    }


def install_service_audit(service_cls: type[Any]) -> None:
    if getattr(service_cls, "_audit_installed", False):
        return

    original_init = service_cls.__init__
    original_add_employee = service_cls.add_employee
    original_update_employee = service_cls.update_employee
    original_delete_employee = service_cls.delete_employee
    original_add_shift = service_cls.add_shift
    original_assign = service_cls.assign
    original_unassign = service_cls.unassign
    original_add_absence = service_cls.add_absence
    original_delete_absence = service_cls.delete_absence
    original_publish_week = service_cls.publish_week
    original_export_schedule = service_cls.export_schedule
    original_export_reports = service_cls.export_reports

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.audit_events: list[AuditEvent] = []

    def record_audit_event(self, action, entity_type, entity_id, before, after, *, user_id="system") -> AuditEvent:
        timestamp = datetime.now()
        normalized_user_id = str(user_id or "system")
        before_json = audit_json(before)
        after_json = audit_json(after)
        previous_hash = max(self.audit_events, key=lambda event: event.timestamp).event_hash if self.audit_events else GENESIS_AUDIT_HASH
        event_hash = calculate_audit_event_hash(
            previous_hash=previous_hash,
            timestamp=timestamp,
            user_id=normalized_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before=before_json,
            after=after_json,
        )
        event = AuditEvent(
            timestamp=timestamp,
            user_id=normalized_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before=before_json,
            after=after_json,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self.audit_events.append(event)
        return event

    def audit_trail(self, limit: int | None = None) -> list[AuditEvent]:
        events = sorted(self.audit_events, key=lambda event: event.timestamp, reverse=True)
        return events[:limit] if limit is not None else events

    def add_employee(self, *args, user_id="system", **kwargs):
        employee = original_add_employee(self, *args, **kwargs)
        self.record_audit_event("employee.created", "employee", employee.id, None, employee_snapshot(employee), user_id=user_id)
        return employee

    def update_employee(self, employee_id, *args, user_id="system", **kwargs):
        employee = self.find_employee(employee_id)
        before = employee_snapshot(employee) if employee is not None else None
        updated = original_update_employee(self, employee_id, *args, **kwargs)
        self.record_audit_event("employee.updated", "employee", updated.id, before, employee_snapshot(updated), user_id=user_id)
        return updated

    def delete_employee(self, employee_id, *, user_id="system"):
        employee = self.find_employee(employee_id)
        if employee is None:
            return False
        before = employee_snapshot(employee)
        assignment_snapshots = [(shift, assignment_snapshot(employee, shift)) for shift in self.shifts if employee_id in shift.employee_ids]
        deleted = original_delete_employee(self, employee_id)
        if deleted:
            for shift, assignment_before in assignment_snapshots:
                self.record_audit_event("assignment.deleted", "assignment", f"{employee_id}:{shift.id}", assignment_before, assignment_snapshot(employee, shift), user_id=user_id)
            self.record_audit_event("employee.deleted", "employee", employee_id, before, None, user_id=user_id)
        return deleted

    def add_shift(self, *args, user_id="system", **kwargs):
        shift = original_add_shift(self, *args, **kwargs)
        self.record_audit_event("shift.created", "shift", shift.id, None, shift_snapshot(shift), user_id=user_id)
        return shift

    def copy_shift(self, shift_id, start=None, end=None, *, user_id="system"):
        source = self.find_shift(shift_id)
        if source is None:
            raise ValueError("Schicht wurde nicht gefunden.")
        duration = source.end - source.start
        copy_start = start or source.start
        copy_end = end or (copy_start + duration)
        return self.add_shift(source.name, source.department, copy_start, copy_end, source.required_employees, source.required_qualification, source.branch, user_id=user_id)

    def update_shift(self, shift_id, name, department, start, end, required_employees, required_qualification="", branch="Zentrale", *, user_id="system"):
        shift = self.find_shift(shift_id)
        if shift is None:
            raise ValueError("Schicht wurde nicht gefunden.")
        before = shift_snapshot(shift)
        updated = Shift(
            id=shift.id,
            employee_ids=list(shift.employee_ids),
            employee_names=list(shift.employee_names),
            name=name,
            department=department,
            start=start,
            end=end,
            required_employees=required_employees,
            required_qualification=required_qualification,
            branch=branch,
            published_at=shift.published_at,
            published_by=shift.published_by,
        )
        if updated.required_employees < len(updated.employee_ids):
            raise ValueError("Kapazität darf nicht kleiner als die aktuelle Besetzung sein.")
        index = self.shifts.index(shift)
        self.shifts[index] = updated
        for employee in self.employees:
            employee.shifts = [updated if item.id == shift.id else item for item in employee.shifts]
        self._remember_department(updated.department)
        self.record_audit_event("shift.updated", "shift", updated.id, before, shift_snapshot(updated), user_id=user_id)
        return updated

    def delete_shift(self, shift_id, *, user_id="system"):
        shift = self.find_shift(shift_id)
        if shift is None:
            return False
        before = shift_snapshot(shift)
        assignment_snapshots = [(employee, assignment_snapshot(employee, shift)) for employee in self.employees if any(item.id == shift.id for item in employee.shifts)]
        self.shifts = [item for item in self.shifts if item.id != shift.id]
        for employee, assignment_before in assignment_snapshots:
            employee.shifts = [item for item in employee.shifts if item.id != shift.id]
            self.record_audit_event("assignment.deleted", "assignment", f"{employee.id}:{shift.id}", assignment_before, assignment_snapshot(employee, shift), user_id=user_id)
        self.record_audit_event("shift.deleted", "shift", shift.id, before, None, user_id=user_id)
        return True

    def assign(self, employee_id, shift_id, *, ignore_profile_mismatch=False, user_id="system"):
        employee = self.find_employee(employee_id)
        shift = self.find_shift(shift_id)
        before = assignment_snapshot(employee, shift) if employee is not None and shift is not None else None
        result: AssignmentResult = original_assign(self, employee_id, shift_id, ignore_profile_mismatch=ignore_profile_mismatch)
        if result.success and employee is not None and shift is not None:
            self.record_audit_event("assignment.created", "assignment", f"{employee.id}:{shift.id}", before, assignment_snapshot(employee, shift), user_id=user_id)
        return result

    def unassign(self, employee_id, shift_id, *, user_id="system"):
        employee = self.find_employee(employee_id)
        shift = self.find_shift(shift_id)
        before = assignment_snapshot(employee, shift) if employee is not None and shift is not None else None
        removed = original_unassign(self, employee_id, shift_id)
        if removed and employee is not None and shift is not None:
            self.record_audit_event("assignment.deleted", "assignment", f"{employee_id}:{shift_id}", before, assignment_snapshot(employee, shift), user_id=user_id)
        return removed

    def add_absence(self, employee_id, start, end, reason="", *, user_id="system"):
        absence = original_add_absence(self, employee_id, start, end, reason)
        self.record_audit_event("absence.created", "absence", absence.id, None, absence_snapshot(absence, employee_id), user_id=user_id)
        return absence

    def delete_absence(self, absence_id, *, user_id="system"):
        before = None
        for employee in self.employees:
            absence = next((item for item in employee.absences if item.id == absence_id), None)
            if absence is not None:
                before = absence_snapshot(absence, employee.id)
                break
        deleted = original_delete_absence(self, absence_id)
        if deleted:
            self.record_audit_event("absence.deleted", "absence", absence_id, before, None, user_id=user_id)
        return deleted

    def publish_week(self, week_start, published_by="Lokaler Modus", *, user_id="system"):
        week_end = week_start + timedelta(days=7)
        week_shifts = [shift for shift in self.shifts if week_start <= shift.start < week_end]
        before = [shift_snapshot(shift) for shift in week_shifts]
        count = original_publish_week(self, week_start, published_by)
        after = [shift_snapshot(shift) for shift in week_shifts]
        self.record_audit_event("schedule.published", "week", week_start.date().isoformat(), before, after, user_id=user_id)
        return count

    def export_schedule(self, path, export_format=ExportFormat.CSV, *, user_id="system", **kwargs):
        output = original_export_schedule(self, path, export_format, **kwargs)
        self.record_audit_event("schedule.exported", "export", str(output), None, {"path": str(output), "format": export_format.value, "shift_count": len(self.shifts)}, user_id=user_id)
        return output

    def export_reports(self, path, *, user_id="system"):
        output = original_export_reports(self, path)
        self.record_audit_event("reports.exported", "export", str(output), None, {"path": str(output), "format": "csv", "metric_count": len(self.create_reports())}, user_id=user_id)
        return output

    service_cls.__init__ = __init__
    service_cls.record_audit_event = record_audit_event
    service_cls.audit_trail = audit_trail
    service_cls.add_employee = add_employee
    service_cls.update_employee = update_employee
    service_cls.delete_employee = delete_employee
    service_cls.add_shift = add_shift
    service_cls.copy_shift = copy_shift
    service_cls.update_shift = update_shift
    service_cls.delete_shift = delete_shift
    service_cls.assign = assign
    service_cls.unassign = unassign
    service_cls.add_absence = add_absence
    service_cls.delete_absence = delete_absence
    service_cls.publish_week = publish_week
    service_cls.export_schedule = export_schedule
    service_cls.export_reports = export_reports
    service_cls._audit_installed = True


def _backfill_audit_hashes(connection) -> None:
    rows = connection.execute(
        """
        SELECT rowid, timestamp, user_id, action, entity_type, entity_id, before, after, previous_hash, event_hash
        FROM audit_events
        ORDER BY timestamp ASC, rowid ASC
        """
    ).fetchall()
    previous_hash = GENESIS_AUDIT_HASH
    for row in rows:
        rowid, timestamp_text, user_id, action, entity_type, entity_id, before, after, stored_previous_hash, stored_event_hash = row
        if stored_previous_hash and stored_event_hash:
            previous_hash = stored_event_hash
            continue
        timestamp = datetime.fromisoformat(timestamp_text)
        event_hash = calculate_audit_event_hash(
            previous_hash=previous_hash,
            timestamp=timestamp,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before or "",
            after=after or "",
        )
        connection.execute(
            "UPDATE audit_events SET previous_hash = ?, event_hash = ? WHERE rowid = ?",
            (previous_hash, event_hash, rowid),
        )
        previous_hash = event_hash


def _insert_repository_audit_event(
    repository: Any,
    action: str,
    entity_type: str,
    entity_id: str,
    before: object | None,
    after: object | None,
    user_id: str,
) -> None:
    """Record an audit event for a repository action that commits immediately.

    Unlike service actions, calls such as user management take effect right
    away instead of being batched until ``save()``. The hash chain is
    therefore extended against the latest row already persisted in the
    database rather than an in-memory list.
    """
    timestamp = datetime.now()
    normalized_user_id = str(user_id or "system")
    before_json = audit_json(before)
    after_json = audit_json(after)
    with repository._connect() as connection:
        row = connection.execute("SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1").fetchone()
        previous_hash = row[0] if row else GENESIS_AUDIT_HASH
        event_hash = calculate_audit_event_hash(
            previous_hash=previous_hash,
            timestamp=timestamp,
            user_id=normalized_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before=before_json,
            after=after_json,
        )
        connection.execute(
            """
            INSERT INTO audit_events(id, timestamp, user_id, action, entity_type, entity_id, before, after, previous_hash, event_hash)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                timestamp.isoformat(),
                normalized_user_id,
                action,
                entity_type,
                str(entity_id),
                before_json,
                after_json,
                previous_hash,
                event_hash,
            ),
        )


def install_repository_audit(repository_cls: type[Any]) -> None:
    if getattr(repository_cls, "_audit_installed", False):
        return

    original_initialize = repository_cls._initialize
    original_save = repository_cls.save
    original_load = repository_cls.load
    original_create_user = repository_cls.create_user
    original_set_user_active = repository_cls.set_user_active
    original_update_user_role = repository_cls.update_user_role
    original_admin_reset_password = repository_cls.admin_reset_password

    def _initialize(self):
        original_initialize(self)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_events(
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL CHECK(length(trim(action)) > 0),
                    entity_type TEXT NOT NULL CHECK(length(trim(entity_type)) > 0),
                    entity_id TEXT NOT NULL,
                    before TEXT NOT NULL DEFAULT '',
                    after TEXT NOT NULL DEFAULT '',
                    previous_hash TEXT NOT NULL DEFAULT '',
                    event_hash TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id);
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(audit_events)").fetchall()}
            if "previous_hash" not in columns:
                connection.execute("ALTER TABLE audit_events ADD COLUMN previous_hash TEXT NOT NULL DEFAULT ''")
            if "event_hash" not in columns:
                connection.execute("ALTER TABLE audit_events ADD COLUMN event_hash TEXT NOT NULL DEFAULT ''")
            _backfill_audit_hashes(connection)

    def save(self, service):
        original_save(self, service)
        audit_events = getattr(service, "audit_events", [])
        if not audit_events:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO audit_events(
                    id, timestamp, user_id, action, entity_type, entity_id, before, after, previous_hash, event_hash
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.id,
                        event.timestamp.isoformat(),
                        event.user_id,
                        event.action,
                        event.entity_type,
                        event.entity_id,
                        event.before,
                        event.after,
                        event.previous_hash,
                        event.event_hash,
                    )
                    for event in audit_events
                ],
            )

    def load(self):
        service = original_load(self)
        if not hasattr(service, "audit_events"):
            service.audit_events = []
        service.audit_events.extend(self.list_audit_events(DEFAULT_AUDIT_LOAD_LIMIT))
        return service

    def list_audit_events(self, limit: int = 200) -> list[AuditEvent]:
        safe_limit = max(1, min(limit, 1000))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, timestamp, user_id, action, entity_type, entity_id, before, after, previous_hash, event_hash
                FROM audit_events
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            AuditEvent(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                user_id=row[2],
                action=row[3],
                entity_type=row[4],
                entity_id=row[5],
                before=row[6] or "",
                after=row[7] or "",
                previous_hash=row[8] or "",
                event_hash=row[9] or "",
            )
            for row in rows
        ]

    def create_user(self, *args, user_id: str = "system", **kwargs):
        user = original_create_user(self, *args, **kwargs)
        _insert_repository_audit_event(self, "user.created", "user", user.id, None, user_snapshot(user), user_id)
        return user

    def set_user_active(self, target_user_id, is_active, *, user_id: str = "system"):
        before_user = self.get_user(target_user_id)
        before = user_snapshot(before_user) if before_user is not None else None
        updated = original_set_user_active(self, target_user_id, is_active)
        action = "user.activated" if is_active else "user.deactivated"
        _insert_repository_audit_event(self, action, "user", target_user_id, before, user_snapshot(updated), user_id)
        return updated

    def update_user_role(self, target_user_id, role, *, user_id: str = "system"):
        before_user = self.get_user(target_user_id)
        before = user_snapshot(before_user) if before_user is not None else None
        updated = original_update_user_role(self, target_user_id, role)
        _insert_repository_audit_event(self, "user.role_changed", "user", target_user_id, before, user_snapshot(updated), user_id)
        return updated

    def admin_reset_password(self, target_user_id, new_password, *, user_id: str = "system"):
        updated = original_admin_reset_password(self, target_user_id, new_password)
        _insert_repository_audit_event(self, "user.password_reset", "user", target_user_id, None, user_snapshot(updated), user_id)
        return updated

    repository_cls._initialize = _initialize
    repository_cls.save = save
    repository_cls.load = load
    repository_cls.create_user = create_user
    repository_cls.set_user_active = set_user_active
    repository_cls.update_user_role = update_user_role
    repository_cls.admin_reset_password = admin_reset_password

    def verify_audit_integrity(self) -> AuditIntegrityResult:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, timestamp, user_id, action, entity_type, entity_id, before, after, previous_hash, event_hash
                FROM audit_events
                ORDER BY timestamp ASC, rowid ASC
                """
            ).fetchall()

        problems: list[str] = []
        expected_previous_hash = GENESIS_AUDIT_HASH
        seen_hashes: set[str] = set()
        for index, row in enumerate(rows, start=1):
            event_id, timestamp_text, user_id, action, entity_type, entity_id, before, after, previous_hash, event_hash = row
            try:
                timestamp = datetime.fromisoformat(timestamp_text)
            except ValueError:
                problems.append(f"Eintrag {index} ({event_id}) hat einen ungültigen Zeitstempel.")
                expected_previous_hash = str(event_hash or "")
                continue
            if previous_hash != expected_previous_hash:
                problems.append(f"Eintrag {index} ({event_id}) verweist auf einen unerwarteten vorherigen Hash.")
            calculated_hash = calculate_audit_event_hash(
                previous_hash=previous_hash or "",
                timestamp=timestamp,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before=before or "",
                after=after or "",
            )
            if event_hash != calculated_hash:
                problems.append(f"Eintrag {index} ({event_id}) wurde nachträglich verändert oder fehlerhaft gespeichert.")
            if event_hash in seen_hashes:
                problems.append(f"Eintrag {index} ({event_id}) verwendet einen doppelten Event-Hash.")
            seen_hashes.add(event_hash)
            expected_previous_hash = str(event_hash or "")
        return AuditIntegrityResult(is_valid=not problems, checked_events=len(rows), problems=problems)

    repository_cls.list_audit_events = list_audit_events
    repository_cls.verify_audit_integrity = verify_audit_integrity
    repository_cls._audit_installed = True
