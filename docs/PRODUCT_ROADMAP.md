# Produkt-Roadmap mit RICE-Bewertung

Diese Roadmap priorisiert Produktinitiativen für den Dienstplaner anhand von RICE. Sie trennt bestätigte Produktanforderungen aus dem Repository von Annahmen, damit strategische Entscheidungen nachvollziehbar bleiben.

## Bewertungsmethode

RICE-Score = `(Reach × Impact × Confidence) / Effort`.

| Faktor | Skala | Bedeutung |
| --- | --- | --- |
| Reach | 1-10 | Anteil der voraussichtlich betroffenen Zielgruppen oder Installationen im nächsten Planungszeitraum. |
| Impact | 1-5 | Erwarteter Nutzen pro betroffener Zielgruppe: 1 = gering, 3 = deutlich, 5 = kritisch. |
| Confidence | 0,5-1,0 | Sicherheit der Bewertung auf Basis bestätigter Anforderungen und technischer Evidenz. |
| Effort | Personentage | Grobe Umsetzungsgröße inklusive Entwicklung, Tests, Dokumentation und Release-Aufwand. |

## Bestätigte Produktanforderungen

Aus dem aktuellen Repository ergeben sich diese bestätigten Anforderungen und Produkteigenschaften:

- Die Anwendung ist eine lokale Python-/Tkinter-Desktop-Anwendung zur Erstellung, Prüfung und Auswertung von Dienstplänen.
- Daten werden lokal in SQLite gespeichert; produktive Nutzung erfordert Prüfung von Backup-Konzept und Zugriffsschutz.
- Es gibt lokale Anmeldung mit Admin-Ersteinrichtung und Admin-Wiederherstellungscode.
- Es existiert ein lokaler Lizenzmechanismus mit signierter Lizenzdatei, Ablaufdatum und maximaler Nutzerzahl.
- Planungsregeln prüfen Kapazität, Qualifikation, Arbeitszeit, Ruhezeit, Pausen, Verfügbarkeit, Abwesenheiten und Zeitkonflikte.
- Forecast-Daten lassen sich aus CSV-Dateien importieren.
- Dienstpläne lassen sich lokal als CSV, Excel-kompatibles HTML oder einfache PDF-Datei exportieren.
- Audit-Funktionalität protokolliert fachliche Änderungen und Exporte als Ereignisse; Integritätsschutz der Audit-Kette ist nicht als bestätigte Anforderung dokumentiert.
- Das Projekt nutzt nur Python-Standardbibliothek und `unittest`.

## Annahmen für die Priorisierung

Diese Roadmap ergänzt die bestätigten Anforderungen um explizite Produktannahmen:

- Primäre Nutzer sind Dienstplanverantwortliche, Administratoren, Geschäftsführung/Controlling sowie Datenschutz- oder Compliance-Verantwortliche in kleinen bis mittleren Betrieben.
- Die nächste Produktphase zielt auf robuste Einzelplatz- oder kleine Mehrplatz-Nutzung, nicht auf mandantenfähigen Cloud-Betrieb.
- Datenschutz, Nachvollziehbarkeit und Wiederherstellbarkeit haben hohen Wert, weil Dienstpläne personenbezogene Daten enthalten und operative Ausfälle direkt den Betrieb treffen.
- Die Anwendung soll weiterhin ohne externe Laufzeitabhängigkeiten funktionieren, solange Nutzen und Risiko keine zusätzliche Abhängigkeit rechtfertigen.
- RICE-Werte sind relative Planungswerte; sie ersetzen keine detaillierte technische Spezifikation oder Aufwandsschätzung vor Sprint-Start.

## Priorisierte Roadmap

| Priorität | Initiative | Status | Reach | Impact | Confidence | Aufwand | RICE | Begründung |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | Datenbankmigrationen | ✅ Umgesetzt | 9 | 5 | 0,85 | 8 | 4,78 | Grundlage für sichere Weiterentwicklung ohne Datenverlust. |
| 2 | Backup/Restore | ✅ Umgesetzt | 8 | 5 | 0,80 | 10 | 3,20 | Reduziert Betriebsrisiko der lokalen SQLite-Datenhaltung. |
| 3 | Benutzer- und Rechteverwaltung in der UI | ✅ Umgesetzt | 8 | 4 | 0,75 | 12 | 2,00 | Macht lokale Anmeldung administrierbar und bereitet Rechteprüfungen vor. |
| 4 | Datenschutzprofile für Exporte | ✅ Umgesetzt | 7 | 4 | 0,70 | 10 | 1,96 | Senkt Risiko bei personenbezogenen Exportdateien. |
| 5 | Import-Fehlerbericht | ✅ Umgesetzt | 6 | 3 | 0,80 | 8 | 1,80 | Verkürzt Fehleranalyse bei Forecast-CSV-Importen. |
| 6 | Kalender-/ICS-Export | ✅ Umgesetzt | 7 | 3 | 0,70 | 9 | 1,63 | Erhöht Nutzbarkeit für Mitarbeitende und operative Kommunikation. |
| 7 | Audit-Integrität | ✅ Umgesetzt | 5 | 5 | 0,65 | 10 | 1,63 | Schützt Nachvollziehbarkeit, benötigt aber klare Compliance-Ziele. |
| 8 | Packaging/Installer | 🟡 Teilweise umgesetzt | 7 | 4 | 0,65 | 12 | 1,52 | Erleichtert Installation, bringt aber Plattform- und Release-Komplexität. |
| 9 | Lizenzdurchsetzung | Offen | 4 | 4 | 0,70 | 8 | 1,40 | Vorhandener Lizenzkern braucht Produktentscheidung zu Enforcement und Support-Fällen. |
| 10 | Automatische Regelvorschläge | Offen | 5 | 4 | 0,50 | 20 | 0,50 | Hoher Nutzen möglich, aber fachlich und technisch unsicher ohne Nutzungsdaten. |

## Initiativen im Detail

### 1. Datenbankmigrationen

- **Zielgruppe:** Entwickler, Administratoren, produktive Betreiber.
- **Nutzen:** Schemaänderungen lassen sich versioniert, wiederholbar und testbar ausrollen. Updates werden planbar, statt manuelle Datenbankeingriffe zu erfordern.
- **Risiko bei Nichtumsetzung:** Neue Funktionen können Dateninkonsistenzen oder Startfehler verursachen. Produktive Datenbanken bleiben schwer supportbar.
- **Aufwandsschätzung:** 8 Personentage.
- **Abhängigkeiten:** SQLite-Repository, Startsequenz, Tests mit bestehenden und leeren Datenbanken, Backup-Empfehlung vor Migration.
- **MVP-Abgrenzung:** Schema-Versionstabelle, sequentielle Migrationsfunktionen, idempotente Ausführung, Tests für Neuinstallation und Upgrade von mindestens einer Vorgängerversion. Kein generisches ORM und kein externer Migrationsdienst.

### 2. Backup/Restore

- **Zielgruppe:** Administratoren, Dienstplanverantwortliche, Betreiber ohne zentrale IT.
- **Nutzen:** Lokale Daten lassen sich vor Updates, vor riskanten Änderungen und nach Geräteausfällen wiederherstellen.
- **Risiko bei Nichtumsetzung:** SQLite-Datei kann durch Bedienfehler, Hardwaredefekte oder fehlerhafte Updates verloren gehen. Wiederherstellung bleibt manuell und fehleranfällig.
- **Aufwandsschätzung:** 10 Personentage.
- **Abhängigkeiten:** Datenbankpfad, Dateisperren, Migrationskonzept, UI-Dialoge, Audit-Ereignis für Backup und Restore.
- **MVP-Abgrenzung:** Manuelles Backup als datierte Datei, Restore mit Sicherheitsabfrage und Integritätsprüfung, Hinweis auf Neustart. Keine Cloud-Synchronisierung und keine inkrementellen Backups.

### 3. Benutzer- und Rechteverwaltung in der UI

- **Status:** Umgesetzt (2026-07-06). UI unter „🔑 Benutzer verwalten" im Kopfbereich, nur für Administratoren sichtbar; Nutzer anlegen, aktivieren/deaktivieren, Rollenwechsel und Passwort-Reset stehen bereit. Ein Schutzmechanismus verhindert das Deaktivieren oder Herabstufen des letzten aktiven Administrators. Alle Aktionen sind Teil der Audit-Hashkette.
- **Zielgruppe:** Administratoren, Teamleitungen, Dienstplanverantwortliche.
- **Nutzen:** Admins können Nutzer anlegen, deaktivieren, Rollen ändern und Passwort-Resets steuern, ohne direkt in Datenbank oder Code einzugreifen.
- **Risiko bei Nichtumsetzung:** Zugangskontrolle bleibt operativ schwach. Geteilte Admin-Zugänge und manuelle Eingriffe erhöhen Sicherheits- und Support-Risiken.
- **Aufwandsschätzung:** 12 Personentage.
- **Abhängigkeiten:** Authentifizierung, Rollenmodell, Lizenzprüfung der maximalen Nutzerzahl, Audit-Protokollierung.
- **MVP-Abgrenzung:** UI für Nutzerliste, Anlegen, Deaktivieren, Rollenwechsel und Passwort-Reset durch Admin. Keine Single-Sign-On-Integration, keine feingranularen Rechte pro Feld.

### 4. Datenschutzprofile für Exporte

- **Status:** Umgesetzt (2026-07-06). Vor jedem Dienstplan-Export wählt man eines der drei MVP-Profile in einem Dialog; die Wahl (inklusive aller Feldeinstellungen) wird im Änderungsverlauf protokolliert. Keine frei konfigurierbare Feldmatrix, wie im MVP vorgesehen.
- **Zielgruppe:** Datenschutzverantwortliche, Dienstplanverantwortliche, Geschäftsführung.
- **Nutzen:** Exporte enthalten nur die für den jeweiligen Zweck notwendigen personenbezogenen Daten.
- **Risiko bei Nichtumsetzung:** CSV-, HTML- oder PDF-Exporte können unnötige personenbezogene Daten enthalten und unkontrolliert weitergegeben werden.
- **Aufwandsschätzung:** 10 Personentage.
- **Abhängigkeiten:** Export-Service, Rollen/Rechte, Audit-Logging, Produktentscheidung zu Standardprofilen.
- **MVP-Abgrenzung:** Drei feste Profile: intern vollständig, Mitarbeitendenplan reduziert, Controlling anonymisiert. Keine frei konfigurierbare Feldmatrix im MVP.

### 5. Import-Fehlerbericht

- **Status:** Umgesetzt (2026-07-07). Fehlerhafte Zeilen blockieren den Import nicht mehr vollständig; ein Dialog listet Zeilennummer, Feld, Schweregrad und Fehlertext je Zeile und lässt sich als CSV speichern. Keine automatische Korrektur der Quelldatei, wie im MVP vorgesehen.
- **Zielgruppe:** Dienstplanverantwortliche, Controlling, Support.
- **Nutzen:** Fehlerhafte Forecast-CSV-Dateien lassen sich zeilenbezogen korrigieren, ohne Trial-and-Error im Importdialog.
- **Risiko bei Nichtumsetzung:** Importprobleme binden Supportzeit und können dazu führen, dass Planung ohne aktuelle Forecast-Daten erfolgt.
- **Aufwandsschätzung:** 8 Personentage.
- **Abhängigkeiten:** Forecast-Parser, Validierungsregeln, UI-Ausgabe, optionaler Export des Fehlerberichts.
- **MVP-Abgrenzung:** Zeilennummer, Feldname, Fehlertext und Schweregrad im Dialog; optional Speichern als CSV. Keine automatische Korrektur von Quelldateien.

### 6. Kalender-/ICS-Export

- **Status:** Umgesetzt (2026-07-07). „Kalender (ICS) Export" exportiert die aktuell angezeigte Woche als RFC-5545-Datei, wahlweise gefiltert auf einen Mitarbeitenden (Service-Ebene) und mit demselben Datenschutzprofil-Dialog wie der CSV/PDF-Export. Zeiten werden als lokale „floating time" ohne Zeitzonen-Konvertierung geschrieben, passend zur restlichen Anwendung. Keine bidirektionale Synchronisierung, keine CalDAV-Anbindung.
- **Zielgruppe:** Mitarbeitende, Dienstplanverantwortliche, Teamleitungen.
- **Nutzen:** Schichten lassen sich in persönliche Kalender übernehmen und mit mobilen Geräten synchronisieren.
- **Risiko bei Nichtumsetzung:** Mitarbeitende müssen Dienstplandaten manuell übertragen. Das erhöht Übertragungsfehler und reduziert Akzeptanz.
- **Aufwandsschätzung:** 9 Personentage.
- **Abhängigkeiten:** Export-Service, Datenschutzprofile, Zeitzonen- und Datumslogik, veröffentlichte Dienstpläne.
- **MVP-Abgrenzung:** ICS-Datei für einen Zeitraum und optional pro Mitarbeitenden. Keine bidirektionale Kalender-Synchronisierung und keine CalDAV-Anbindung.

### 7. Audit-Integrität

- **Zielgruppe:** Administratoren, Compliance-Verantwortliche, Geschäftsführung.
- **Nutzen:** Audit-Ereignisse werden manipulationserschwerend verkettet oder signiert. Änderungen bleiben glaubwürdiger nachvollziehbar.
- **Risiko bei Nichtumsetzung:** Bestehende Audit-Einträge können lokal verändert oder gelöscht werden, ohne dass die Anwendung dies sicher erkennt.
- **Aufwandsschätzung:** 10 Personentage.
- **Abhängigkeiten:** Persistente Audit-Speicherung, Schlüssel-/Secret-Strategie, Backup/Restore, Datenbankmigrationen.
- **MVP-Abgrenzung:** Hash-Kette pro Audit-Ereignis mit Prüfwerkzeug und Warnung bei Inkonsistenz. Kein revisionssicheres externes Archiv und keine qualifizierte elektronische Signatur.

### 8. Packaging/Installer

- **Status:** Teilweise umgesetzt (2026-07-07). Versionsanzeige in Titelleiste und Kopfbereich der Anwendung ist umgesetzt und getestet. `scripts/windows_installer.iss` (Inno Setup) erzeugt einen Startmenüeintrag, optionales Desktop-Icon und entfernt beim Deinstallieren nie das Datenverzeichnis – konnte aber in dieser Linux-Umgebung nicht tatsächlich kompiliert oder auf einem Windows-System durchgespielt werden. Vor dem ersten Kundenversand einmal real auf Windows bauen und die Installation/Deinstallation verifizieren, dann auf „Umgesetzt" setzen.
- **Zielgruppe:** Endnutzer, Administratoren, Support, Vertrieb.
- **Nutzen:** Installation und Updates werden reproduzierbar. Support kann sich auf definierte Installationspfade und Versionen beziehen.
- **Risiko bei Nichtumsetzung:** Nutzer müssen Python, Tkinter und Startskripte korrekt einrichten. Installationsfehler bremsen Einführung und Support.
- **Aufwandsschätzung:** 12 Personentage.
- **Abhängigkeiten:** Release-Prozess, Zielplattformen, Lizenzdateipfad, Datenverzeichnis, Code-Signing-Entscheidung.
- **MVP-Abgrenzung:** Windows-Installer oder portables Paket mit Startmenüeintrag, Versionsanzeige und dokumentiertem Datenpfad. Kein automatischer Updater im MVP.

### 9. Lizenzdurchsetzung

- **Zielgruppe:** Betreiber, Vertrieb, Support, Produktverantwortliche.
- **Nutzen:** Gültigkeit, Ablauf und Nutzerlimit werden konsistent geprüft und verständlich kommuniziert.
- **Risiko bei Nichtumsetzung:** Lizenzstatus bleibt uneinheitlich durchsetzbar. Supportfälle bei abgelaufenen oder falsch installierten Lizenzen nehmen zu.
- **Aufwandsschätzung:** 8 Personentage.
- **Abhängigkeiten:** Vorhandener Lizenzmanager, Nutzerverwaltung, Startsequenz, UI-Meldungen, Notfall-/Grace-Policy.
- **MVP-Abgrenzung:** Startprüfung mit klarer Fehlermeldung, Anzeige des Lizenzstatus, Durchsetzung des Nutzerlimits bei aktiven Nutzern. Keine Online-Aktivierung und kein Lizenzserver.

### 10. Automatische Regelvorschläge

- **Zielgruppe:** Dienstplanverantwortliche, Teamleitungen.
- **Nutzen:** Die Anwendung schlägt bei Regelverstößen konkrete Alternativen vor, z. B. geeignete Mitarbeitende oder konfliktfreie Schichten.
- **Risiko bei Nichtumsetzung:** Planer müssen Regelverletzungen manuell analysieren und beheben. Das kostet Zeit und erhöht die Fehlerwahrscheinlichkeit.
- **Aufwandsschätzung:** 20 Personentage.
- **Abhängigkeiten:** Regel-Engine, vollständige Datenqualität, UI für Vorschläge, Erklärbarkeit der Vorschlagslogik, Performance-Tests bei größeren Dienstplänen.
- **MVP-Abgrenzung:** Deterministische Vorschläge auf Basis bestehender harter Regeln für einzelne Konflikte. Keine KI-Optimierung, keine automatische Umplanung ganzer Wochen.

## Nächste empfohlene Schritte

1. Datenbankmigrationen spezifizieren und als technische Grundlage vor funktionsreichen Änderungen umsetzen.
2. Backup/Restore direkt danach liefern, damit Updates und Migrationen operativ abgesichert sind.
3. Produktentscheidung zu Rollen, Lizenz-Enforcement und Datenschutzprofilen treffen, weil diese drei Themen fachlich zusammenhängen.
4. Für automatische Regelvorschläge erst reale Planungsfehler sammeln und Erfolgskriterien definieren, bevor die Umsetzung startet.
