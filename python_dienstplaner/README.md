# Dienstplaner Python

Python-Implementierung des Dienstplaners mit Tkinter-Oberfläche, SQLite-Persistenz und Tests auf Basis der Standardbibliothek.

## Start

```bash
python start_python_dienstplaner.py
```

Unter Windows kann die Anwendung alternativ per Doppelklick auf `start_python_dienstplaner.bat` gestartet werden. Die Batch-Datei prüft, ob `py -3` oder `python` verfügbar ist, setzt den Projektordner als Arbeitsverzeichnis und zeigt Fehlermeldungen im Konsolenfenster an.

## Zuweisungen

Im Dialog „Mitarbeitenden zuweisen“ kann optional aktiviert werden, dass Abteilung, Filiale und Qualifikation für die konkrete Zuweisung ignoriert werden. Andere harte Regeln wie Kapazität, aktive Mitarbeitende, Arbeitszeit, Ruhezeit, Abwesenheit und Zeitkonflikte bleiben aktiv.

## Abwesenheiten

Im Dialog „Abwesenheit erfassen“ stehen typische Gründe wie Urlaub, freier Tag, Krank, Fortbildung und Seminar zur Auswahl. Der Grund bleibt editierbar, damit auch betriebliche Sonderfälle erfasst werden können.

## Datenhaltung

Die Anwendung nutzt nur die Python-Standardbibliothek (`tkinter`, `sqlite3`, `csv`). Persistente Daten landen standardmäßig in `python_dienstplaner/data/dienstplaner.sqlite3`.

## CSV-Forecast

Forecast-CSV mit dem Format `FilialeId;Filiale;Datum;Umsatz;Kunden` importieren.

Beispiel:

```text
FilialeId;Filiale;Datum;Umsatz;Kunden
1;Zentrale;01.01.2026;1234,50;120
```

## Tests

```bash
python -m unittest discover -s tests -p 'test_python_*.py'
```
