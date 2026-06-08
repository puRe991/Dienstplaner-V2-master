# Dienstplaner

Python-Desktop-Anwendung zur Erstellung, Prüfung und Auswertung von Dienstplänen. Der Dienstplaner unterstützt Verantwortliche dabei, Mitarbeitende regelkonform Schichten zuzuweisen, Planungsdaten lokal zu speichern und relevante Informationen zu exportieren.

> **Projektstatus:** Dieses Repository enthält ausschließlich die Python-Version. Frühere nicht-Python-Artefakte wurden entfernt.

## Funktionsumfang

- **Mitarbeiter- und Schichtplanung:** Mitarbeitende und Schichten anlegen, bearbeiten, löschen und zuweisen; bei Bedarf kann eine Zuweisung Abteilung, Filiale und Qualifikation bewusst ignorieren.
- **Regelbasierte Validierung:** Prüfung von Kapazität, Qualifikation, Arbeitszeit, Ruhezeit, Pausen, Verfügbarkeit, Abwesenheit und Zeitkonflikten.
- **Wochenansicht:** Dienstplan als Desktop-Oberfläche mit Kalender, Mitarbeiterliste, Schichtübersicht und Statusmeldungen.
- **Abwesenheiten:** Abwesenheiten erfassen und Überschneidungen mit bestehenden Schichten verhindern.
- **Forecast-Import:** Umsatz- und Kundenfrequenzdaten aus CSV-Dateien importieren.
- **Export:** Dienstpläne lokal als CSV, Excel-kompatibles HTML oder einfache PDF-Datei ausgeben.
- **Persistenz:** Lokale SQLite-Datenbank für Mitarbeitende, Schichten, Zuweisungen und Abwesenheiten.

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
python -m unittest discover -s tests -p 'test_python_*.py'
```

Die Tests prüfen die Planungsregeln, Zuweisungen, Abwesenheitslogik, Exporte, Forecast-Importe und SQLite-Persistenz.

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
