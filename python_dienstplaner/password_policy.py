from __future__ import annotations

import string


MIN_PASSWORD_LENGTH = 12
_WEAK_PASSWORDS = {
    "12345678",
    "admin",
    "admin123",
    "password",
    "passwort",
    "qwerty",
    "letmein",
}


def validate_password(password: str) -> None:
    """Validate local account passwords.

    The policy deliberately favors length and avoids a rigid requirement for
    specific character classes. Requiring two character groups blocks common
    single-pattern passwords while still allowing memorable passphrases with
    separators or numbers.
    """
    if not isinstance(password, str):
        raise ValueError("Passwort ist erforderlich.")

    if not password.strip():
        raise ValueError("Passwort darf nicht leer sein oder nur aus Leerzeichen bestehen.")

    normalized_password = password.strip().casefold()
    if normalized_password in _WEAK_PASSWORDS:
        raise ValueError("Dieses Passwort ist zu leicht zu erraten. Bitte wählen Sie ein anderes Passwort.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen lang sein.")

    if _character_group_count(password) < 2:
        raise ValueError(
            "Passwort muss mindestens zwei verschiedene Zeichenarten enthalten, "
            "zum Beispiel Buchstaben und Zahlen oder Sonderzeichen."
        )


def _character_group_count(password: str) -> int:
    groups = 0
    groups += any(character.islower() for character in password)
    groups += any(character.isupper() for character in password)
    groups += any(character.isdigit() for character in password)
    groups += any(
        character in string.punctuation or (not character.isalnum() and not character.isspace())
        for character in password
    )
    return groups
