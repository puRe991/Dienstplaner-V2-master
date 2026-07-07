# Dienstplaner

Python-Desktop-Anwendung zur Erstellung, Prüfung und Auswertung von Dienstplänen. Der Dienstplaner unterstützt Verantwortliche dabei, Mitarbeitende regelkonform Schichten zuzuweisen, Planungsdaten lokal zu speichern und relevante Informationen zu exportieren.

> **Projektstatus:** Dieses Repository enthält ausschließlich die Python-Version. Frühere nicht-Python-Artefakte wurden entfernt.

## Funktionsumfang

- **Mitarbeiter- und Schichtplanung:** Mitarbeitende und Schichten anlegen, bearbeiten, löschen und zuweisen; bei Bedarf kann eine Zuweisung Abteilung, Filiale und Qualifikation bewusst ignorieren.
- **Regelbasierte Validierung:** Prüfung von Kapazität, Qualifikation, Arbeitszeit, Ruhezeit, Pausen, Verfügbarkeit, Abwesenheit und Zeitkonflikten.
- **Wochenansicht:** Dienstplan als Desktop-Oberfläche mit Kalender, Mitarbeiterliste, Schichtübersicht und Statusmeldungen.
- **Abwesenheiten:** Urlaub, freie Tage, Krankheit, Fortbildung, Seminar und weitere Abwesenheitsarten erfassen; Überschneidungen mit bestehenden Schichten werden verhindert.
- **Forecast-Import mit Fehlerbericht:** Umsatz- und Kundenfrequenzdaten aus CSV-Dateien importieren. Fehlerhafte Zeilen blockieren nicht den gesamten Import: ein Fehlerbericht zeigt Zeilennummer, Feldname, Schweregrad und Fehlertext pro Zeile und lässt sich als CSV speichern.
- **Export mit Datenschutzprofilen:** Dienstpläne lokal als CSV, Excel-kompatibles HTML oder einfache PDF-Datei ausgeben. Vor jedem Export wählt man eines von drei festen Profilen: „Intern vollständig" (mit Löhnen und Abwesenheitsgründen), „Mitarbeitendenplan reduziert" (ohne Löhne/Abwesenheitsgründe, nur veröffentlichte Schichten) oder „Controlling anonymisiert" (Personalkosten sichtbar, Namen anonymisiert).
- **Kalender-Export (ICS):** Die aktuell angezeigte Woche lässt sich als iCalendar-Datei (.ics) exportieren und in persönliche Kalender-Apps importieren; auch hier gilt das gewählte Datenschutzprofil.
- **Persistenz:** Lokale SQLite-Datenbank für Mitarbeitende, Schichten, Zuweisungen und Abwesenheiten.
- **Lokale Anmeldung:** Beim ersten Start wird ein Admin angelegt. Ein einmaliger Admin-Wiederherstellungscode ermöglicht das Anlegen eines neuen Admins, falls Benutzername oder Passwort vergessen wurden.
- **Benutzerverwaltung:** Administratoren können über **Benutzer verwalten** im Hauptfenster weitere Nutzer anlegen, deaktivieren/aktivieren, die Rolle ändern und Passwörter zurücksetzen. Mindestens ein aktiver Administrator bleibt dabei immer erhalten; alle Änderungen werden im Änderungsverlauf protokolliert.

## Technologie

| Bereich | Technologie |
| --- | --- |
| Anwendung | Python 3, Tkinter |
| Persistenz | SQLite über `sqlite3` |
| Tests | `unittest` |
| Abhängigkeiten | Nur Python-Standardbibliothek |
| CI | GitHub Actions mit Python-Testlauf |

## Voraussetzungen

- Python 3.10 oder neuer
- Tkinter-Unterstützung der Python-Installation
- Git

Unter Windows wird Tkinter in der Regel mit Python installiert. Unter Linux muss je nach Distribution ein Paket wie `python3-tk` installiert sein.

## Schnellstart

### 1. Repository klonen

```bash
git clone <REPOSITORY-URL>
cd Dienstplaner-V2-master
```

### 2. Anwendung starten

```bash
python start_python_dienstplaner.py
```

Unter Windows kann die Anwendung alternativ per Doppelklick auf `start_python_dienstplaner.bat` gestartet werden. Die Batch-Datei sucht `py -3` oder `python`, setzt den Projektordner als Arbeitsverzeichnis und hält das Konsolenfenster bei Fehlern offen.

## Tests und Qualitätssicherung

```bash
python -m unittest discover -s tests
```

Die Tests prüfen die Planungsregeln, Zuweisungen, Abwesenheitslogik, Exporte, Forecast-Importe, SQLite-Persistenz und die Audit-Integrität (Hash-Kette).

## Projektstruktur

```text
.
├── .github/workflows/ci.yml          # Python-Testlauf in GitHub Actions
├── python_dienstplaner/              # Anwendungscode
│   ├── app.py                        # Tkinter-Oberfläche und Desktop-Shell
│   ├── models.py                     # Domänenmodelle
│   ├── repository.py                 # SQLite-Persistenz
│   ├── rules.py                      # Fachliche Planungsregeln
│   ├── services.py                   # Planungs-, Export- und Forecast-Services
│   └── README.md                     # Kurzdokumentation für das Python-Paket
├── tests/                            # unittest-Testfälle
├── start_python_dienstplaner.py      # Startskript
└── start_python_dienstplaner.bat     # Windows-Startskript
```

## Datenhaltung

Die Anwendung speichert Daten standardmäßig in:

```text
python_dienstplaner/data/dienstplaner.sqlite3
```

Der Ordner `python_dienstplaner/data/` wird bei Bedarf automatisch angelegt und ist nicht für Quellcode gedacht. Prüfe vor produktiver Nutzung, ob lokale SQLite-Datenhaltung, Backup-Konzept und Zugriffsschutz zu deiner Einsatzumgebung passen.

## Admin-Zugang wiederherstellen

Beim Einrichten des ersten Administrators zeigt die Anwendung einen Admin-Wiederherstellungscode an. Bewahre diesen Code getrennt vom Gerät und sicher auf. Wer diesen Code besitzt, kann über **Admin-Zugang wiederherstellen** im Anmeldefenster einen neuen lokalen Administrator anlegen. Nach erfolgreicher Wiederherstellung entwertet die Anwendung den alten Code und zeigt einen neuen Code an.

Ohne gespeicherten Wiederherstellungscode kann die Anwendung ein vergessenes Admin-Passwort nicht entschlüsseln, weil Passwörter nur gehasht gespeichert werden. In diesem Fall bleibt nur die Wiederherstellung aus einem Backup oder ein administrativer Datenbankeingriff.

## Rollen und Benutzerverwaltung

Es gibt drei lokale Rollen:

| Rolle | Berechtigungen |
| --- | --- |
| Administrator | Alle Rechte, inklusive Benutzerverwaltung, Regelprofile und Änderungsverlauf. |
| Planer | Dienstpläne veröffentlichen, exportieren, Abwesenheiten verwalten. Keine Mitarbeiter-, Rollen- oder Benutzerverwaltung. |
| Betrachter | Nur Lesezugriff auf die Planungsansicht. |

Administratoren erreichen die Benutzerverwaltung über den Button **🔑 Benutzer verwalten** im Kopfbereich der Anwendung. Dort lassen sich Nutzer anlegen, aktivieren/deaktivieren, in der Rolle ändern und ihr Passwort zurücksetzen. Die Anwendung verhindert, dass der letzte aktive Administrator deaktiviert oder herabgestuft wird, damit der Zugang nicht versehentlich verloren geht. Jede Änderung wird mit Zeitstempel und ausführendem Benutzer im Änderungsverlauf protokolliert.

## Forecast-CSV

Der Forecast-Import erwartet Semikolon-getrennte Dateien mit Kopfzeile:

```text
FilialeId;Filiale;Datum;Umsatz;Kunden
1;Zentrale;01.01.2026;1234,50;120
```

## Hinweise für Weiterentwicklung

- Trenne geplante Zeiten klar von echten Ist-Zeiten aus Zeiterfassungssystemen.
- Prüfe personenbezogene Exportdateien und die SQLite-Datenbank auf ausreichenden Zugriffsschutz.
- Ergänze bei produktiver Nutzung eine Authentifizierung und ein Berechtigungskonzept.
- Halte neue Funktionen in `python_dienstplaner/services.py` testbar und decke Edge Cases in `tests/` ab.

## Versionierung

Die App-Version steht zentral in `python_dienstplaner/__init__.py` als `__version__`. Erhöhe die Version vor jedem Release nach semantischer Versionierung:

- Patch-Version für reine Fehlerkorrekturen.
- Minor-Version für kompatible neue Funktionen oder Datenbankmigrationen.
- Major-Version für nicht kompatible Änderungen.

## Datenbankmigrationen

`python_dienstplaner/repository.py` verwaltet das SQLite-Schema über die Tabelle `schema_version`. Jede Migration hat eine fortlaufende Nummer und läuft nur, wenn die gespeicherte Version kleiner ist. Die Migrationsschritte sind idempotent aufgebaut: `CREATE TABLE IF NOT EXISTS`, Spaltenprüfung per `PRAGMA table_info` und defensive Nacharbeiten erlauben einen sicheren Neustart nach abgebrochenen Updates.

Release-Regeln für Schemaänderungen:

1. Neue Schemaänderung als neue nummerierte Migration ergänzen.
2. `SCHEMA_VERSION` erhöhen.
3. Migration so schreiben, dass sie auf teilweise migrierten Datenbanken erneut laufen kann.
4. Test für eine neue Datenbank und mindestens eine alte Testdatenbank ergänzen.
5. Vor dem Release eine Sicherung produktiver SQLite-Dateien erstellen.

## Build und Release

### Lokaler Prüflauf

```bash
python -m unittest discover -s tests
```

### Release-Checkliste

1. Version in `python_dienstplaner/__init__.py` erhöhen.
2. Datenbankmigrationen und Tests abschließen.
3. Tests lokal ausführen.
4. README und Upgrade-Hinweise aktualisieren.
5. Git-Tag erstellen, z. B. `v0.2.0`.
6. Release-Artefakte bauen und Prüfsummen veröffentlichen.

## Windows-Packaging mit PyInstaller

Optional kann eine Windows-Distribution mit PyInstaller erstellt werden:

```powershell
py -3 -m pip install pyinstaller
py -3 scripts/build_windows_pyinstaller.py
```

Das Ergebnis in `dist/Dienstplaner/` ist bereits ein portables Paket: Der Ordner lässt sich kopieren und `Dienstplaner.exe` darin direkt starten, ohne Installation.

Hinweise:

- Lege ein Windows-Icon als `assets/dienstplaner.ico` ab. Das Skript bindet es automatisch ein.
- Lege eine `LICENSE`-Datei im Repository-Root ab. Das Skript fügt sie dem Build hinzu, wenn sie vorhanden ist.
- Speichere produktive Daten außerhalb des Programmordners. Der sichere Standard-Launcher nutzt in PyInstaller-Builds `%APPDATA%\Dienstplaner\data\dienstplaner.sqlite3`; alternativ kannst du `DIENSTPLANER_DATABASE_PATH` setzen. Der Entwicklungspfad `python_dienstplaner/data/dienstplaner.sqlite3` bleibt nur für den Quellcode-Start aktiv.
- Überschreibe bei Upgrades nie ungeprüft das Datenverzeichnis. Sichere zuerst die SQLite-Datei und starte danach die neue Version, damit die Migrationen kontrolliert laufen.
- Wenn ein Upgrade fehlschlägt, nutze die Sicherung der SQLite-Datei und prüfe die Fehlermeldung, bevor du erneut migrierst.
- Die aktuelle Version steht in der Titelleiste und im Kopfbereich der Anwendung (`v<Version>`), damit Nutzende und Support jederzeit erkennen, welcher Stand installiert ist.

### Windows-Installer mit Startmenüeintrag (Inno Setup)

Für Kunden, die keine portable ZIP-Datei möchten, gibt es zusätzlich ein [Inno Setup](https://jrsoftware.org/isinfo.php)-Skript unter `scripts/windows_installer.iss`. Es baut auf dem PyInstaller-Ordner auf und erzeugt einen Startmenüeintrag (optional Desktop-Icon), zeigt die Version im Windows-Deinstallationsdialog an und entfernt beim Deinstallieren ausschließlich die Programmdateien – niemals `%APPDATA%\Dienstplaner\data` mit Datenbank, Backups und Lizenzdatei.

```powershell
py -3 scripts/build_windows_pyinstaller.py
iscc /DAppVersion=0.6.0 scripts\windows_installer.iss
```

Der fertige Installer liegt danach unter `dist/installer/Dienstplaner-Setup-<Version>.exe`. Ersetze `0.6.0` durch den aktuellen Wert aus `python_dienstplaner/__init__.py`.

> Hinweis: Das Inno-Setup-Skript wurde sorgfältig gegen die dokumentierte Inno-Setup-Syntax geprüft, konnte aber in dieser Umgebung nicht kompiliert werden, da hier weder Windows noch Inno Setup verfügbar sind. Vor dem ersten Kundenversand einmal auf einem echten Windows-System bauen und den Installationsvorgang inklusive Deinstallation durchspielen.
