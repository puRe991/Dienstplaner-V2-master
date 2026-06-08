from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .auth import Permission, User, UserRole
from .repository import SQLiteSchedulerRepository


def authenticate_on_start(parent: tk.Tk, repository: SQLiteSchedulerRepository) -> User:
    """Run first-admin setup or login and return the authenticated user.

    The function is intentionally outside app.py so UI conflicts in the main
    scheduler shell stay small when authentication behavior changes.
    """
    user: User | None = run_initial_setup(parent, repository) if repository.user_count() == 0 else None
    while user is None:
        user = run_login_dialog(parent, repository)
        if user is None:
            parent.destroy()
            raise SystemExit("Login abgebrochen.")
    return user


def run_initial_setup(parent: tk.Tk, repository: SQLiteSchedulerRepository) -> User | None:
    dialog = tk.Toplevel(parent)
    dialog.title("Ersten Administrator einrichten")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.configure(bg="#FFFFFF")
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)
    result: dict[str, User | None] = {"user": None}
    values = {
        "username": tk.StringVar(value="admin"),
        "display_name": tk.StringVar(value="Administrator"),
        "password": tk.StringVar(),
        "repeat": tk.StringVar(),
    }
    tk.Label(dialog, text="Initialer Administrator", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 8))
    tk.Label(dialog, text="Legen Sie den ersten lokalen Admin an. Das Passwort wird mit Salt gehasht gespeichert.", bg="#FFFFFF", fg="#334155", wraplength=360, justify="left").grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))
    for row, (key, label) in enumerate([("username", "Benutzername"), ("display_name", "Anzeigename"), ("password", "Passwort"), ("repeat", "Passwort wiederholen")], start=2):
        tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=6)
        ttk.Entry(dialog, textvariable=values[key], width=34, show="*" if key in {"password", "repeat"} else "").grid(row=row, column=1, padx=18, pady=6)

    def create_admin() -> None:
        if values["password"].get() != values["repeat"].get():
            messagebox.showerror("Setup fehlgeschlagen", "Die Passwörter stimmen nicht überein.", parent=dialog)
            return
        try:
            result["user"] = repository.create_user(values["username"].get(), values["password"].get(), UserRole.ADMIN, values["display_name"].get())
            dialog.destroy()
        except ValueError as exc:
            messagebox.showerror("Setup fehlgeschlagen", str(exc), parent=dialog)

    ttk.Button(dialog, text="Administrator anlegen", style="Primary.TButton", command=create_admin).grid(row=6, column=1, sticky="e", padx=18, pady=(12, 18))
    parent.wait_window(dialog)
    return result["user"]


def run_login_dialog(parent: tk.Tk, repository: SQLiteSchedulerRepository) -> User | None:
    dialog = tk.Toplevel(parent)
    dialog.title("Anmelden")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.configure(bg="#FFFFFF")
    result: dict[str, User | None] = {"user": None}
    username = tk.StringVar()
    password = tk.StringVar()
    tk.Label(dialog, text="Anmelden", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))
    for row, (label, variable, show) in enumerate([("Benutzername", username, ""), ("Passwort", password, "*")], start=1):
        tk.Label(dialog, text=label, bg="#FFFFFF", fg="#334155").grid(row=row, column=0, sticky="w", padx=18, pady=7)
        ttk.Entry(dialog, textvariable=variable, width=34, show=show).grid(row=row, column=1, padx=18, pady=7)

    def login() -> None:
        user = repository.authenticate_user(username.get(), password.get())
        if user is None:
            messagebox.showerror("Anmeldung fehlgeschlagen", "Benutzername oder Passwort ist falsch.", parent=dialog)
            return
        result["user"] = user
        dialog.destroy()

    ttk.Button(dialog, text="Anmelden", style="Primary.TButton", command=login).grid(row=3, column=1, sticky="e", padx=18, pady=(12, 18))
    dialog.bind("<Return>", lambda _event: login())
    parent.wait_window(dialog)
    return result["user"]


def user_label(user: User | None) -> str:
    if user is None:
        return "Nicht angemeldet"
    return f"{user.display_name}\nRolle: {user.role.value}"


def user_has_permission(user: User | None, permission: Permission) -> bool:
    return user is not None and user.has_permission(permission)
