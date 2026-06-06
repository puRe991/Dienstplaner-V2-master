from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import Employee, Shift
from .services import SchedulerService


class SQLiteSchedulerRepository:
    """Small SQLite persistence layer for the standalone Python version.

    The repository stores the Python application's own data under python_dienstplaner/data
    by default and does not read from or write to the original C#/SQL Server setup.
    """

    def __init__(self, database_path: str | Path = "python_dienstplaner/data/dienstplaner.sqlite3") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, service: SchedulerService) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM assignments")
            connection.execute("DELETE FROM shifts")
            connection.execute("DELETE FROM employees")
            connection.executemany(
                """
                INSERT INTO employees(id, name, department, qualification, weekly_hours_limit, branch, hourly_wage, is_active)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
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
                    )
                    for employee in service.employees
                ],
            )
            connection.executemany(
                """
                INSERT INTO shifts(id, name, department, start, end, required_employees, required_qualification, branch)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
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
                    )
                    for shift in service.shifts
                ],
            )
            connection.executemany(
                "INSERT INTO assignments(employee_id, shift_id) VALUES(?, ?)",
                [(employee.id, shift.id) for employee in service.employees for shift in employee.shifts],
            )

    def load(self) -> SchedulerService:
        service = SchedulerService()
        with self._connect() as connection:
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
                )
                for row in connection.execute(
                    "SELECT id, name, department, qualification, weekly_hours_limit, branch, hourly_wage, is_active FROM employees ORDER BY name"
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
                )
                for row in connection.execute(
                    "SELECT id, name, department, start, end, required_employees, required_qualification, branch FROM shifts ORDER BY start, name"
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
                    is_active INTEGER NOT NULL CHECK(is_active IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS shifts(
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    required_employees INTEGER NOT NULL CHECK(required_employees > 0),
                    required_qualification TEXT NOT NULL,
                    branch TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assignments(
                    employee_id TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                    shift_id TEXT NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
                    PRIMARY KEY(employee_id, shift_id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
