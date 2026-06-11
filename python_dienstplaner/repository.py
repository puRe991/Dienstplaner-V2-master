from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .auth import User, UserRole
from .models import Absence, Employee, RevenueForecast, RuleProfile, Shift
from .services import SchedulerService


PASSWORD_ITERATIONS = 200_000
PASSWORD_SALT_BYTES = 16

RULE_PROFILE_COLUMNS: tuple[str, ...] = (
    "id",
    "name",
    "min_rest_hours",
    "max_daily_hours",
    "break_after_six_hours_minutes",
    "break_after_nine_hours_minutes",
    "weekly_hours_limit_is_hard",
    "daily_hours_limit_is_hard",
    "rest_time_is_hard",
    "profile_mismatch_is_hard",
    "missing_availability_is_hard",
    "insufficient_break_is_hard",
    "is_active",
)

RULE_PROFILE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rule_profiles(
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK(length(trim(name)) > 0),
    min_rest_hours REAL NOT NULL CHECK(min_rest_hours >= 0),
    max_daily_hours REAL NOT NULL CHECK(max_daily_hours > 0),
    break_after_six_hours_minutes INTEGER NOT NULL CHECK(break_after_six_hours_minutes >= 0),
    break_after_nine_hours_minutes INTEGER NOT NULL
        CHECK(break_after_nine_hours_minutes >= break_after_six_hours_minutes),
    weekly_hours_limit_is_hard INTEGER NOT NULL CHECK(weekly_hours_limit_is_hard IN (0, 1)),
    daily_hours_limit_is_hard INTEGER NOT NULL CHECK(daily_hours_limit_is_hard IN (0, 1)),
    rest_time_is_hard INTEGER NOT NULL CHECK(rest_time_is_hard IN (0, 1)),
    profile_mismatch_is_hard INTEGER NOT NULL CHECK(profile_mismatch_is_hard IN (0, 1)),
    missing_availability_is_hard INTEGER NOT NULL CHECK(missing_availability_is_hard IN (0, 1)),
    insufficient_break_is_hard INTEGER NOT NULL CHECK(insufficient_break_is_hard IN (0, 1)),
    is_active INTEGER NOT NULL CHECK(is_active IN (0, 1))
);
"""


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
            connection.execute("DELETE FROM rule_profiles")
            connection.executemany(
                """
                INSERT INTO rule_profiles(
                    id, name, min_rest_hours, max_daily_hours, break_after_six_hours_minutes,
                    break_after_nine_hours_minutes, weekly_hours_limit_is_hard, daily_hours_limit_is_hard,
                    rest_time_is_hard, profile_mismatch_is_hard, missing_availability_is_hard,
                    insufficient_break_is_hard, is_active
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        profile.id,
                        profile.name,
                        profile.min_rest_hours,
                        profile.max_daily_hours,
                        profile.break_after_six_hours_minutes,
                        profile.break_after_nine_hours_minutes,
                        1 if profile.weekly_hours_limit_is_hard else 0,
                        1 if profile.daily_hours_limit_is_hard else 0,
                        1 if profile.rest_time_is_hard else 0,
                        1 if profile.profile_mismatch_is_hard else 0,
                        1 if profile.missing_availability_is_hard else 0,
                        1 if profile.insufficient_break_is_hard else 0,
                        1 if profile.is_active else 0,
                    )
                    for profile in service.rule_profiles
                ],
            )
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
            rule_profiles = [
                RuleProfile(
                    id=row[0],
                    name=row[1],
                    min_rest_hours=row[2],
                    max_daily_hours=row[3],
                    break_after_six_hours_minutes=row[4],
                    break_after_nine_hours_minutes=row[5],
                    weekly_hours_limit_is_hard=bool(row[6]),
                    daily_hours_limit_is_hard=bool(row[7]),
                    rest_time_is_hard=bool(row[8]),
                    profile_mismatch_is_hard=bool(row[9]),
                    missing_availability_is_hard=bool(row[10]),
                    insufficient_break_is_hard=bool(row[11]),
                    is_active=bool(row[12]),
                )
                for row in connection.execute(
                    """
                    SELECT id, name, min_rest_hours, max_daily_hours, break_after_six_hours_minutes,
                           break_after_nine_hours_minutes, weekly_hours_limit_is_hard, daily_hours_limit_is_hard,
                           rest_time_is_hard, profile_mismatch_is_hard, missing_availability_is_hard,
                           insufficient_break_is_hard, is_active
                    FROM rule_profiles
                    ORDER BY is_active DESC, name COLLATE NOCASE
                    """
                )
            ]
            if rule_profiles:
                service.rule_profiles = rule_profiles
                service._ensure_single_active_rule_profile()
                service.rules.profile = service.active_rule_profile
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

    def user_count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    def create_user(self, username: str, password: str, role: UserRole | str, display_name: str = "") -> User:
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("Benutzername ist erforderlich.")
        if len(password) < 8:
            raise ValueError("Passwort muss mindestens 8 Zeichen lang sein.")
        user_role = role if isinstance(role, UserRole) else UserRole(str(role))
        salt, password_hash = self._hash_password(password)
        user = User(
            username=normalized_username,
            display_name=display_name.strip() or normalized_username,
            role=user_role,
            password_salt=salt,
            password_hash=password_hash,
        )
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO users(id, username, display_name, role, password_hash, password_salt, is_active, created_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user.id,
                        user.username,
                        user.display_name,
                        user.role.value,
                        user.password_hash,
                        user.password_salt,
                        1 if user.is_active else 0,
                        user.created_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Benutzername existiert bereits.") from exc
        return user

    def authenticate_user(self, username: str, password: str) -> User | None:
        normalized_username = username.strip()
        if not normalized_username or not password:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, display_name, role, password_hash, password_salt, is_active, created_at
                FROM users
                WHERE lower(username) = lower(?)
                """,
                (normalized_username,),
            ).fetchone()
        if row is None or not bool(row[6]):
            return None
        if not self._verify_password(password, row[5], row[4]):
            return None
        return User(
            id=row[0],
            username=row[1],
            display_name=row[2] or row[1],
            role=UserRole(row[3]),
            password_hash=row[4],
            password_salt=row[5],
            is_active=bool(row[6]),
            created_at=datetime.fromisoformat(row[7]),
        )

    def list_users(self) -> list[User]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, username, display_name, role, password_hash, password_salt, is_active, created_at
                FROM users
                ORDER BY username COLLATE NOCASE
                """
            ).fetchall()
        return [
            User(
                id=row[0],
                username=row[1],
                display_name=row[2] or row[1],
                role=UserRole(row[3]),
                password_hash=row[4],
                password_salt=row[5],
                is_active=bool(row[6]),
                created_at=datetime.fromisoformat(row[7]),
            )
            for row in rows
        ]

    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        password_salt = salt or secrets.token_hex(PASSWORD_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(password_salt), PASSWORD_ITERATIONS)
        return password_salt, digest.hex()

    @classmethod
    def _verify_password(cls, password: str, salt: str, expected_hash: str) -> bool:
        try:
            _, actual_hash = cls._hash_password(password, salt)
        except ValueError:
            return False
        return hmac.compare_digest(actual_hash, expected_hash)

    @staticmethod
    def _assignment_rows(connection: sqlite3.Connection) -> Iterable[tuple[str, str]]:
        return connection.execute("SELECT employee_id, shift_id FROM assignments")

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                f"""
                CREATE TABLE IF NOT EXISTS users(
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK(length(trim(username)) > 0),
                    display_name TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL CHECK(role IN ('admin', 'planner', 'viewer')),
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
                    created_at TEXT NOT NULL
                );
                {RULE_PROFILE_TABLE_SQL}
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
            self._migrate_rule_profiles(connection)
            self._ensure_default_rule_profile(connection)
            self._ensure_column(connection, "employees", "break_minutes_per_shift", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "absences", "id", "TEXT")
            for rowid, in connection.execute("SELECT rowid FROM absences WHERE id IS NULL OR id = ''"):
                connection.execute("UPDATE absences SET id = ? WHERE rowid = ?", (str(uuid4()), rowid))
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_absences_id ON absences(id)")
            self._ensure_column(connection, "shifts", "published_at", "TEXT")
            self._ensure_column(connection, "shifts", "published_by", "TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _migrate_rule_profiles(connection: sqlite3.Connection) -> None:
        """Upgrade partially-created rule profile tables from earlier builds.

        SQLite cannot add primary keys, UNIQUE constraints, or CHECK constraints to
        an existing table. Rebuilding the table keeps old profile values where
        possible and prevents startup/save failures when a user has already run a
        build with an incomplete rule_profiles schema.
        """
        current_columns = [
            row[1] for row in connection.execute("PRAGMA table_info(rule_profiles)")
        ]
        if set(RULE_PROFILE_COLUMNS).issubset(current_columns):
            return

        legacy_table = f"rule_profiles_legacy_{uuid4().hex}"
        connection.execute(f"ALTER TABLE rule_profiles RENAME TO {legacy_table}")
        connection.execute(RULE_PROFILE_TABLE_SQL)
        legacy_columns = [
            row[1] for row in connection.execute(f"PRAGMA table_info({legacy_table})")
        ]
        rows = (
            connection.execute(f"SELECT {', '.join(legacy_columns)} FROM {legacy_table}").fetchall()
            if legacy_columns
            else []
        )

        used_names: set[str] = set()
        used_ids: set[str] = set()
        for index, row in enumerate(rows, start=1):
            values = dict(zip(legacy_columns, row))
            profile = SQLiteSchedulerRepository._rule_profile_from_legacy_row(values, index, used_names, used_ids)
            used_names.add(profile.name.casefold())
            used_ids.add(profile.id)
            SQLiteSchedulerRepository._insert_rule_profile(connection, profile)
        connection.execute(f"DROP TABLE {legacy_table}")

    @staticmethod
    def _rule_profile_from_legacy_row(
        values: dict[str, object], index: int, used_names: set[str], used_ids: set[str]
    ) -> RuleProfile:
        defaults = RuleProfile()
        name = SQLiteSchedulerRepository._legacy_text(
            values.get("name"), f"Migriertes Regelprofil {index}"
        )
        original_name = name
        suffix = index
        while name.casefold() in used_names:
            name = f"{original_name} {suffix}"
            suffix += 1

        profile_id = SQLiteSchedulerRepository._legacy_text(values.get("id"), str(uuid4()))
        while profile_id in used_ids:
            profile_id = str(uuid4())

        break_after_six = SQLiteSchedulerRepository._legacy_int(
            values.get("break_after_six_hours_minutes"), defaults.break_after_six_hours_minutes
        )
        break_after_nine = SQLiteSchedulerRepository._legacy_int(
            values.get("break_after_nine_hours_minutes"), defaults.break_after_nine_hours_minutes
        )
        if break_after_nine < break_after_six:
            break_after_nine = break_after_six

        return RuleProfile(
            id=profile_id,
            name=name,
            min_rest_hours=SQLiteSchedulerRepository._legacy_float(
                values.get("min_rest_hours"), defaults.min_rest_hours
            ),
            max_daily_hours=SQLiteSchedulerRepository._legacy_positive_float(
                values.get("max_daily_hours"), defaults.max_daily_hours
            ),
            break_after_six_hours_minutes=break_after_six,
            break_after_nine_hours_minutes=break_after_nine,
            weekly_hours_limit_is_hard=SQLiteSchedulerRepository._legacy_bool(
                values.get("weekly_hours_limit_is_hard"), defaults.weekly_hours_limit_is_hard
            ),
            daily_hours_limit_is_hard=SQLiteSchedulerRepository._legacy_bool(
                values.get("daily_hours_limit_is_hard"), defaults.daily_hours_limit_is_hard
            ),
            rest_time_is_hard=SQLiteSchedulerRepository._legacy_bool(
                values.get("rest_time_is_hard"), defaults.rest_time_is_hard
            ),
            profile_mismatch_is_hard=SQLiteSchedulerRepository._legacy_bool(
                values.get("profile_mismatch_is_hard"), defaults.profile_mismatch_is_hard
            ),
            missing_availability_is_hard=SQLiteSchedulerRepository._legacy_bool(
                values.get("missing_availability_is_hard"), defaults.missing_availability_is_hard
            ),
            insufficient_break_is_hard=SQLiteSchedulerRepository._legacy_bool(
                values.get("insufficient_break_is_hard"), defaults.insufficient_break_is_hard
            ),
            is_active=SQLiteSchedulerRepository._legacy_bool(values.get("is_active"), defaults.is_active),
        )

    @staticmethod
    def _insert_rule_profile(connection: sqlite3.Connection, profile: RuleProfile) -> None:
        connection.execute(
            """
            INSERT INTO rule_profiles(
                id, name, min_rest_hours, max_daily_hours, break_after_six_hours_minutes,
                break_after_nine_hours_minutes, weekly_hours_limit_is_hard, daily_hours_limit_is_hard,
                rest_time_is_hard, profile_mismatch_is_hard, missing_availability_is_hard,
                insufficient_break_is_hard, is_active
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.id,
                profile.name,
                profile.min_rest_hours,
                profile.max_daily_hours,
                profile.break_after_six_hours_minutes,
                profile.break_after_nine_hours_minutes,
                1 if profile.weekly_hours_limit_is_hard else 0,
                1 if profile.daily_hours_limit_is_hard else 0,
                1 if profile.rest_time_is_hard else 0,
                1 if profile.profile_mismatch_is_hard else 0,
                1 if profile.missing_availability_is_hard else 0,
                1 if profile.insufficient_break_is_hard else 0,
                1 if profile.is_active else 0,
            ),
        )

    @staticmethod
    def _legacy_text(value: object, default: str) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _legacy_float(value: object, default: float) -> float:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return default
        return numeric_value if numeric_value >= 0 else default

    @staticmethod
    def _legacy_positive_float(value: object, default: float) -> float:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return default
        return numeric_value if numeric_value > 0 else default

    @staticmethod
    def _legacy_int(value: object, default: int) -> int:
        try:
            numeric_value = int(value)
        except (TypeError, ValueError):
            return default
        return numeric_value if numeric_value >= 0 else default

    @staticmethod
    def _legacy_bool(value: object, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "ja"}
        return bool(value)

    @staticmethod
    def _ensure_default_rule_profile(connection: sqlite3.Connection) -> None:
        count = int(connection.execute("SELECT COUNT(*) FROM rule_profiles").fetchone()[0])
        if count:
            return
        SQLiteSchedulerRepository._insert_rule_profile(connection, RuleProfile())

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


from .audit import install_repository_audit
install_repository_audit(SQLiteSchedulerRepository)
