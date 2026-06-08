from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .models import Absence, Employee, RevenueForecast, Shift
from .services import SchedulerService


class SQLiteSchedulerRepository:
    """SQLite persistence layer for the Python Dienstplaner application.

    The repository stores application data under python_dienstplaner/data by default.
    """

    def __init__(self, database_path: str | Path = "python_dienstplaner/data/dienstplaner.sqlite3") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, service: SchedulerService) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM assignments")
            connection.execute("DELETE FROM absences")
            connection.execute("DELETE FROM forecasts")
            connection.execute("DELETE FROM departments")
            connection.execute("DELETE FROM shifts")
            connection.execute("DELETE FROM employees")
            connection.executemany(
                "INSERT OR IGNORE INTO departments(name) VALUES(?)",
                [(department,) for department in service.department_options()],
            )
            connection.executemany(
                """
                INSERT INTO employees(
                    id, name, department, qualification, weekly_hours_limit, branch,
                    hourly_wage, is_active, break_minutes_per_shift
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        employee.id,
                        employee.name,
                        employee.department,
                        employee.qualification,
                        employee.weekly_hours_limit,
                        employee.branch,
                        employee.hourly_wage,
                        1 if employee.is_active else 0,
                        employee.break_minutes_per_shift,
                    )
                    for employee in service.employees
                ],
            )
            connection.executemany(
                """
                INSERT INTO shifts(
                    id, name, department, start, end, required_employees, required_qualification,
                    branch, published_at, published_by
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        shift.id,
                        shift.name,
                        shift.department,
                        shift.start.isoformat(),
                        shift.end.isoformat(),
                        shift.required_employees,
                        shift.required_qualification,
                        shift.branch,
                        shift.published_at.isoformat() if shift.published_at else None,
                        shift.published_by,
                    )
                    for shift in service.shifts
                ],
            )
            connection.executemany(
                "INSERT INTO assignments(employee_id, shift_id) VALUES(?, ?)",
                [(employee.id, shift.id) for employee in service.employees for shift in employee.shifts],
            )
            connection.executemany(
                "INSERT INTO absences(id, employee_id, start, end, reason) VALUES(?, ?, ?, ?, ?)",
                [
                    (absence.id, employee.id, absence.start.isoformat(), absence.end.isoformat(), absence.reason)
                    for employee in service.employees
                    for absence in employee.absences
                ],
            )
            connection.executemany(
                """
                INSERT INTO forecasts(branch_id, branch, date, expected_revenue, expected_customers)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(branch_id, date) DO UPDATE SET
                    branch = excluded.branch,
                    expected_revenue = excluded.expected_revenue,
                    expected_customers = excluded.expected_customers
                """,
                [
                    (
                        forecast.branch_id,
                        forecast.branch,
                        forecast.date.date().isoformat(),
                        forecast.expected_revenue,
                        forecast.expected_customers,
                    )
                    for forecast in service.forecasts
                ],
            )

    def load(self) -> SchedulerService:
        service = SchedulerService()
        with self._connect() as connection:
            departments = [row[0] for row in connection.execute("SELECT name FROM departments ORDER BY name COLLATE NOCASE")]
            if departments:
                service.departments = departments
            employees = {
                row[0]: Employee(
                    id=row[0],
                    name=row[1],
                    department=row[2],
                    qualification=row[3],
                    weekly_hours_limit=row[4],
                    branch=row[5],
                    hourly_wage=row[6],
                    is_active=bool(row[7]),
                    break_minutes_per_shift=row[8],
                )
                for row in connection.execute(
                    """
                    SELECT id, name, department, qualification, weekly_hours_limit, branch,
                           hourly_wage, is_active, break_minutes_per_shift
                    FROM employees
                    ORDER BY name
                    """
                )
            }
            shifts = {
                row[0]: Shift(
                    id=row[0],
                    name=row[1],
                    department=row[2],
                    start=datetime.fromisoformat(row[3]),
                    end=datetime.fromisoformat(row[4]),
                    required_employees=row[5],
                    required_qualification=row[6],
                    branch=row[7],
                    published_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    published_by=row[9] or "",
                )
                for row in connection.execute(
                    """
                    SELECT id, name, department, start, end, required_employees,
                           required_qualification, branch, published_at, published_by
                    FROM shifts
                    ORDER BY start, name
                    """
                )
            }
            for employee_id, shift_id in self._assignment_rows(connection):
                employee = employees.get(employee_id)
                shift = shifts.get(shift_id)
                if employee is None or shift is None:
                    continue
                employee.shifts.append(shift)
                shift.employee_ids.append(employee.id)
                shift.employee_names.append(employee.name)

            for absence_id, employee_id, start, end, reason in connection.execute("SELECT id, employee_id, start, end, reason FROM absences"):
                employee = employees.get(employee_id)
                if employee is None:
                    continue
                employee.absences.append(Absence(datetime.fromisoformat(start), datetime.fromisoformat(end), reason or "", id=absence_id))

            service.forecasts.extend(
                RevenueForecast(
                    branch_id=row[0],
                    branch=row[1],
                    date=datetime.fromisoformat(row[2]),
                    expected_revenue=row[3],
                    expected_customers=row[4],
                )
                for row in connection.execute(
                    "SELECT branch_id, branch, date, expected_revenue, expected_customers FROM forecasts ORDER BY date, branch"
                )
            )

        service.employees.extend(employees.values())
        service.shifts.extend(shifts.values())
        return service

    @staticmethod
    def _assignment_rows(connection: sqlite3.Connection) -> Iterable[tuple[str, str]]:
        return connection.execute("SELECT employee_id, shift_id FROM assignments")

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS employees(
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    qualification TEXT NOT NULL,
                    weekly_hours_limit INTEGER NOT NULL CHECK(weekly_hours_limit > 0),
                    branch TEXT NOT NULL,
                    hourly_wage REAL NOT NULL CHECK(hourly_wage >= 0),
                    is_active INTEGER NOT NULL CHECK(is_active IN (0, 1)),
                    break_minutes_per_shift INTEGER NOT NULL DEFAULT 0 CHECK(break_minutes_per_shift >= 0)
                );
                CREATE TABLE IF NOT EXISTS departments(
                    name TEXT PRIMARY KEY CHECK(length(trim(name)) > 0)
                );
                CREATE TABLE IF NOT EXISTS shifts(
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    required_employees INTEGER NOT NULL CHECK(required_employees > 0),
                    required_qualification TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    published_at TEXT,
                    published_by TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS assignments(
                    employee_id TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                    shift_id TEXT NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
                    PRIMARY KEY(employee_id, shift_id)
                );
                CREATE TABLE IF NOT EXISTS absences(
                    id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS forecasts(
                    branch_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    date TEXT NOT NULL,
                    expected_revenue REAL NOT NULL CHECK(expected_revenue >= 0),
                    expected_customers INTEGER NOT NULL CHECK(expected_customers >= 0),
                    PRIMARY KEY(branch_id, date)
                );
                """
            )
            self._ensure_column(connection, "employees", "break_minutes_per_shift", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "absences", "id", "TEXT")
            for rowid, in connection.execute("SELECT rowid FROM absences WHERE id IS NULL OR id = ''"):
                connection.execute("UPDATE absences SET id = ? WHERE rowid = ?", (str(uuid4()), rowid))
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_absences_id ON absences(id)")
            self._ensure_column(connection, "shifts", "published_at", "TEXT")
            self._ensure_column(connection, "shifts", "published_by", "TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
