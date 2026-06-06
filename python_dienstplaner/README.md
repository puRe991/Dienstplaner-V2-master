# Dienstplaner Python

Separate Python-Implementierung des Dienstplaners. Diese Version liegt vollständig im Ordner `python_dienstplaner/` und berührt den vorhandenen C#-/WPF-Code nicht.

## Start

```bash
python start_python_dienstplaner.py
```

Die Anwendung nutzt nur die Python-Standardbibliothek (`tkinter`, `sqlite3`, `csv`). Persistente Daten landen standardmäßig in `python_dienstplaner/data/dienstplaner.sqlite3`.

## Funktionsumfang

- Mitarbeitende und Schichten anlegen.
- Mitarbeitende Schichten zuweisen.
- Harte Planungsregeln prüfen: Kapazität, aktive Mitarbeitende, Doppelzuweisung, Abteilung, Filiale, Qualifikation, Wochenstundenlimit, Tageshöchstarbeitszeit, Ruhezeit, Zeitkonflikte und Abwesenheiten.
- Weiche Warnungen erzeugen: fehlende Verfügbarkeit und lange Schichten.
- Reports für Personalkosten, Besetzungsgrad, Überstunden und Regelverstöße berechnen.
- Dienstplan als CSV oder Textdatei exportieren.
- Forecast-CSV mit dem Format `FilialeId;Filiale;Datum;Umsatz;Kunden` importieren.

## Tests

```bash
python -m unittest discover -s tests -p 'test_python_*.py'
```
