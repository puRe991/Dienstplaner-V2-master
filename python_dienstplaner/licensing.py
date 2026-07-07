from __future__ import annotations

import base64
import json
import os
import sys
from dataclasses import asdict
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import LicenseInfo


SHA256_DIGESTINFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
DEFAULT_PUBLIC_KEY = (
    int(
        "c03803f8f52df4cf9f32210a461e98f92536ae6e47ffecdebbfde797060200fa"
        "6e2eebbb386e7df058e43f0a3e3514ff192225b80531c1ef626043b20c0ba"
        "377d3f5193d18a6866465409e62cf19b2126108ff1838b0de9101034e4c15"
        "9e546de098650f2d0d2186b8b636ca336f1500025b5bbbe691ff781384902"
        "4689cc4ffd17b014b1e6964d8d25a472ed8fb1198a3b4d8ae2edf657a797"
        "5a44aac6c84e219bc1984b116f39e4032106d36bb757daa109dcfdfa0aac4"
        "ffab4ff4f1c2a55009873b3636d2fb51fe36a82b5434c17ca7c45c33f324"
        "6e9c1c6f891ec879e0f1831474fb355994eb9d5906bb78f949f7e8264177"
        "f61b7c9d619063d1da19aaeb",
        16,
    ),
    65537,
)
LICENSE_PATH_ENV = "DIENSTPLANER_LICENSE_PATH"
APP_DATA_DIR_NAME = "DienstplanerPro"
LICENSE_FILE_NAME = "license.json"
TRIAL_FILE_NAME = "trial.json"
DEFAULT_TRIAL_PERIOD_DAYS = 30


class LicenseError(ValueError):
    """Raised when a license file cannot be parsed into a valid license model."""


class LicenseCheckResult:
    """Immutable-style result for application startup license checks."""

    def __init__(
        self,
        valid: bool,
        message: str,
        license_info: LicenseInfo | None = None,
        *,
        is_trial: bool = False,
    ) -> None:
        self.valid = valid
        self.message = message
        self.license_info = license_info
        self.is_trial = is_trial

    @property
    def company_name(self) -> str:
        if self.license_info is not None:
            return self.license_info.company_name
        return "Testversion" if self.is_trial else "Keine Lizenz"

    @property
    def display_text(self) -> str:
        if self.license_info is None:
            return self.message
        return f"{self.company_name} · gültig bis {self.license_info.valid_until:%d.%m.%Y}"


class LicenseManager:
    """Load and verify local license files.

    The signature is an RSA PKCS#1 v1.5 signature over a canonical JSON
    representation of all license fields except ``signature``. Only the public
    key is required in customer installations, so changing license fields breaks
    verification without exposing signing material in the application.
    """

    def __init__(
        self,
        license_path: str | Path | None = None,
        public_key: tuple[int, int] = DEFAULT_PUBLIC_KEY,
        private_key: tuple[int, int] | None = None,
        trial_path: str | Path | None = None,
        trial_period_days: int = DEFAULT_TRIAL_PERIOD_DAYS,
    ) -> None:
        self.license_path = Path(license_path) if license_path is not None else default_license_path()
        self.public_key = public_key
        self.private_key = private_key
        self.trial_path = Path(trial_path) if trial_path is not None else self.license_path.with_name(TRIAL_FILE_NAME)
        self.trial_period_days = trial_period_days

    def check(self, *, current_user_count: int = 0, today: date | None = None) -> LicenseCheckResult:
        today = today or date.today()
        if not self.license_path.exists():
            return self._check_trial(today)

        try:
            license_info = self.load()
        except (OSError, json.JSONDecodeError, LicenseError) as exc:
            return LicenseCheckResult(False, f"Lizenzdatei ist ungültig: {exc}")

        if not self.verify_signature(license_info):
            return LicenseCheckResult(False, "Lizenzsignatur ist ungültig oder die Lizenz wurde verändert.", license_info)
        if license_info.valid_until < today:
            return LicenseCheckResult(False, f"Lizenz ist seit {license_info.valid_until:%d.%m.%Y} abgelaufen.", license_info)
        if current_user_count > license_info.max_users:
            return LicenseCheckResult(
                False,
                f"Lizenz erlaubt maximal {license_info.max_users} aktive Nutzer; aktuell vorhanden: {current_user_count}.",
                license_info,
            )
        return LicenseCheckResult(True, "Lizenz gültig.", license_info)

    def import_license_text(self, content: str, *, current_user_count: int = 0, today: date | None = None) -> LicenseCheckResult:
        """Validate a pasted/received license (raw JSON text) and install it if genuine.

        Used to let a customer unlock the app from within the UI after purchase,
        without requiring them to manually locate the platform-specific license
        file path. Only installs the license when its signature checks out, so a
        bad paste can't clobber a working license with garbage.
        """
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise LicenseError("Die Lizenz muss ein JSON-Objekt enthalten.")
            license_info = license_from_dict(data)
        except (json.JSONDecodeError, LicenseError) as exc:
            return LicenseCheckResult(False, f"Lizenz ist ungültig: {exc}")

        if not self.verify_signature(license_info):
            return LicenseCheckResult(False, "Lizenzsignatur ist ungültig oder die Lizenz wurde verändert.", license_info)

        self.save(license_info)
        return self.check(current_user_count=current_user_count, today=today)

    def load(self) -> LicenseInfo:
        data = json.loads(self.license_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise LicenseError("Die Lizenzdatei muss ein JSON-Objekt enthalten.")
        return license_from_dict(data)

    def save(self, license_info: LicenseInfo) -> Path:
        self.license_path.parent.mkdir(parents=True, exist_ok=True)
        self.license_path.write_text(json.dumps(license_to_dict(license_info), indent=2, ensure_ascii=False), encoding="utf-8")
        return self.license_path

    def sign(self, license_info: LicenseInfo) -> str:
        if self.private_key is None:
            raise LicenseError("Zum Signieren ist ein privater Lizenzschlüssel erforderlich.")
        return sign_license(license_info, self.private_key)

    def verify_signature(self, license_info: LicenseInfo) -> bool:
        return verify_license_signature(license_info, self.public_key)

    def _check_trial(self, today: date) -> LicenseCheckResult:
        """Allow the app to run without a license file for a limited trial period.

        The trial start date is recorded on first launch (next to where the
        license file would live) so reinstalling the app or deleting an
        already-expired license cannot restart the clock.
        """
        trial_start = self._trial_start_date(today)
        days_remaining = self.trial_period_days - (today - trial_start).days
        if days_remaining > 0:
            return LicenseCheckResult(
                True,
                f"Testversion: noch {days_remaining} von {self.trial_period_days} Tagen ohne Lizenz nutzbar.",
                is_trial=True,
            )
        return LicenseCheckResult(
            False,
            f"Die {self.trial_period_days}-tägige Testphase ist abgelaufen. Bitte aktivieren Sie eine Lizenz, "
            "um die Anwendung weiter zu nutzen.",
            is_trial=True,
        )

    def _trial_start_date(self, today: date) -> date:
        try:
            data = json.loads(self.trial_path.read_text(encoding="utf-8"))
            return datetime.strptime(str(data["trial_start"]), "%Y-%m-%d").date()
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            self.trial_path.parent.mkdir(parents=True, exist_ok=True)
            self.trial_path.write_text(json.dumps({"trial_start": today.isoformat()}), encoding="utf-8")
            return today


def default_license_path() -> Path:
    configured = os.environ.get(LICENSE_PATH_ENV)
    if configured:
        return Path(configured).expanduser()

    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_DATA_DIR_NAME / LICENSE_FILE_NAME


def sign_license(license_info: LicenseInfo, private_key: tuple[int, int]) -> str:
    modulus, private_exponent = private_key
    encoded = _encoded_message(license_info, _modulus_length(modulus))
    signature = pow(int.from_bytes(encoded, "big"), private_exponent, modulus).to_bytes(_modulus_length(modulus), "big")
    return base64.urlsafe_b64encode(signature).decode("ascii")


def verify_license_signature(license_info: LicenseInfo, public_key: tuple[int, int]) -> bool:
    modulus, exponent = public_key
    try:
        signature = base64.b64decode(license_info.signature.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError):
        return False
    key_length = _modulus_length(modulus)
    if len(signature) != key_length:
        return False
    recovered = pow(int.from_bytes(signature, "big"), exponent, modulus).to_bytes(key_length, "big")
    try:
        expected = _encoded_message(license_info, key_length)
    except LicenseError:
        return False
    return recovered == expected


def _encoded_message(license_info: LicenseInfo, key_length: int) -> bytes:
    digest_info = SHA256_DIGESTINFO_PREFIX + sha256(canonical_license_payload(license_info).encode("utf-8")).digest()
    padding_length = key_length - len(digest_info) - 3
    if padding_length < 8:
        raise LicenseError("Der RSA-Schlüssel ist zu kurz für SHA-256-Signaturen.")
    return b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info


def _modulus_length(modulus: int) -> int:
    return (modulus.bit_length() + 7) // 8


def canonical_license_payload(license_info: LicenseInfo) -> str:
    payload = license_to_dict(license_info)
    payload.pop("signature", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def license_to_dict(license_info: LicenseInfo) -> dict[str, Any]:
    data = asdict(license_info)
    data["valid_until"] = license_info.valid_until.isoformat()
    return data


def license_from_dict(data: dict[str, Any]) -> LicenseInfo:
    required = {"company_name", "license_id", "valid_until", "max_users", "features", "signature"}
    missing = sorted(required.difference(data))
    if missing:
        raise LicenseError("Fehlende Lizenzfelder: " + ", ".join(missing))

    company_name = _required_string(data["company_name"], "company_name")
    license_id = _required_string(data["license_id"], "license_id")
    signature = _required_string(data["signature"], "signature")
    try:
        valid_until = datetime.strptime(_required_string(data["valid_until"], "valid_until"), "%Y-%m-%d").date()
    except ValueError as exc:
        raise LicenseError("valid_until muss im Format YYYY-MM-DD vorliegen.") from exc

    if not isinstance(data["max_users"], int) or isinstance(data["max_users"], bool) or data["max_users"] <= 0:
        raise LicenseError("max_users muss eine positive Ganzzahl sein.")
    if not isinstance(data["features"], list) or not all(isinstance(item, str) and item.strip() for item in data["features"]):
        raise LicenseError("features muss eine Liste nicht leerer Zeichenketten sein.")

    return LicenseInfo(
        company_name=company_name,
        license_id=license_id,
        valid_until=valid_until,
        max_users=data["max_users"],
        features=[item.strip() for item in data["features"]],
        signature=signature,
    )


def _required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LicenseError(f"{field_name} muss eine nicht leere Zeichenkette sein.")
    return value.strip()
