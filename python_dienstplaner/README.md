# Dienstplaner Python

Separate Python-Implementierung des Dienstplaners. Diese Version liegt vollständig im Ordner `python_dienstplaner/` und berührt den vorhandenen C#-/WPF-Code nicht.

## Start

```bash
python start_python_dienstplaner.py
```

Unter Windows kann die Anwendung alternativ per Doppelklick auf `start_python_dienstplaner.bat` gestartet werden. Die Batch-Datei prüft, ob `py -3` oder `python` verfügbar ist, setzt den Projektordner als Arbeitsverzeichnis und zeigt Fehlermeldungen im Konsolenfenster an.

Die Anwendung nutzt nur die Python-Standardbibliothek (`tkinter`, `sqlite3`, `csv`). Persistente Daten landen standardmäßig in `python_dienstplaner/data/dienstplaner.sqlite3`.

## Funktionsumfang

- Dashboard-Oberfläche im Stil der Dienstplanung-Pro-Vorlage mit Kopfbereich, Navigation, Wochenraster, Kennzahlenkarten, Kalender, Abwesenheiten und Schnellaktionen.
- Keine Demo-Stammdaten: Ein neuer Datenbestand startet leer und wird ausschließlich über die Oberfläche gepflegt.
- Mitarbeitende anlegen, bearbeiten, deaktivieren oder löschen; Mitarbeitendenstammdaten werden mit bestehenden Zuweisungen synchronisiert.
- Abwesenheiten erfassen und per Doppelklick löschen; Überschneidungen mit bestehenden Schichten werden blockiert.
- Schichten anlegen, bearbeiten, löschen, suchen, im Wochenraster auswählen und Mitarbeitenden regelgeprüft zuweisen.
- Harte Planungsregeln prüfen: Kapazität, aktive Mitarbeitende, Doppelzuweisung, Abteilung, Filiale, Qualifikation, Wochenstundenlimit, Tageshöchstarbeitszeit, Ruhezeit, Zeitkonflikte und Abwesenheiten.
- Weiche Warnungen erzeugen: fehlende Verfügbarkeit und lange Schichten.
- Abwesenheiten, Mitarbeitende, Schichten und Zuweisungen vollständig in SQLite speichern und laden.
- Reports für Personalkosten, Besetzungsgrad, Überstunden und Regelverstöße berechnen.
- Dienstplan als CSV oder Textdatei exportieren.
- Forecast-CSV mit dem Format `FilialeId;Filiale;Datum;Umsatz;Kunden` importieren.

## Tests

```bash
python -m unittest discover -s tests -p 'test_python_*.py'
```
