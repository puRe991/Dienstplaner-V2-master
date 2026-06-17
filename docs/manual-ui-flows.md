# Manuell zu prüfende UI-Flows

Diese Checkliste ergänzt die automatisierten Tests. Sie prüft gezielt die zentralisierte Fehlerbehandlung über `_run_ui_action` und das lokale Logfile-Konzept.

## Speichern

1. Anwendung starten und einen Test-Dienstplan öffnen.
2. Eine kleine Änderung durchführen, z. B. eine Schicht anlegen.
3. **Speichern** auslösen.
4. Erwartung: Die Statusleiste zeigt eine erfolgreiche Speichermeldung. Es erscheint kein Fehlerdialog.
5. Optional: Datenbank kurzfristig sperren oder Schreibrechte entziehen.
6. Erwartung im Fehlerfall: Die Statusleiste meldet den technischen Fehler generisch, der Dialog zeigt keine sensiblen Daten, und das lokale Logfile enthält Aktion und Fehlertyp.

## Export

1. **CSV Export** auslösen und je eine `.csv`, `.txt` und `.pdf`-Datei in ein Testverzeichnis schreiben.
2. Erwartung: Die Statusleiste nennt nur Zielpfad/Erfolgsmeldung aus der bestehenden Exportfunktion; das Logfile enthält keine vollständigen Exportinhalte.
3. Einen nicht beschreibbaren Zielpfad wählen.
4. Erwartung: Technischer Fehlerdialog ohne personenbezogene Exportdaten; Logfile enthält keine vollständigen Mitarbeitendenlisten.

## Forecast-Import

1. Eine valide Forecast-CSV importieren.
2. Erwartung: Statusleiste nennt Anzahl der importierten und neu gespeicherten Zeilen.
3. Eine ungültige CSV importieren.
4. Erwartung: Fachfehler erscheint als verständliche Warnung; technische Details bleiben im Logfile.

## Veröffentlichen

1. Einen vollständig besetzten Wochenplan veröffentlichen.
2. Erwartung: Statusleiste nennt Anzahl gespeicherter Schichten und die Ansicht aktualisiert sich.
3. Einen Wochenplan mit offenen Slots veröffentlichen.
4. Erwartung: Fachfehler erscheint als Warnung, kein technischer Fehlerdialog.

## Datenschutzprüfung Logfile

1. App-Datenverzeichnis öffnen: Windows `%LOCALAPPDATA%/Dienstplanung Pro`, macOS `~/Library/Application Support/Dienstplanung Pro`, Linux `${XDG_STATE_HOME:-~/.local/state}/dienstplanung-pro`.
2. `dienstplaner.log` prüfen.
3. Erwartung: Das Log enthält Aktionsnamen, Event-Status, Fehlertypen und redigierte Kurzdetails. Es enthält keine Passwörter, Recovery-Codes, Tokens oder vollständige personenbezogene Exportdaten.
