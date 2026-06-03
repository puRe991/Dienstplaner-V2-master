# Release-Konzept für Release 1

## 1. Zweck und Release-Bezeichnung

**Release 1 wird als kontrollierter Pilot-Release bezeichnet.** Es ist ausdrücklich
weder ein allgemein verfügbarer Beta-Release noch ein produktiver Release. Der
Pilot soll belegen, dass ein kleiner Betrieb seinen Dienstplan über einen
vollständigen Wochenzyklus zuverlässig erstellen, veröffentlichen, anzeigen und
wiederherstellen kann.

Der Pilot darf erst starten, wenn alle Abnahmekriterien in Abschnitt 6 erfüllt
sind. Vorschaufunktionen sind nicht Teil der Freigabeentscheidung. Nach dem
Pilot ist eine dokumentierte Auswertung mit Entscheidung über Nacharbeiten,
einen erweiterten Pilot oder die Vorbereitung eines produktiven Releases
vorgesehen.

## 2. Zielgruppe und vorgesehener Betriebsmodus

Release 1 richtet sich an **einen kleinen Pilotbetrieb mit genau einer Filiale**.
Der verbindlich unterstützte Umfang ist:

| Merkmal | Unterstützter Umfang in Release 1 |
| --- | --- |
| Mandanten | 1 Pilotbetrieb / 1 Mandant |
| Filialen | genau 1 Filiale |
| Mitarbeitende | bis zu 30 aktive Mitarbeitende |
| Benutzerkonten | bis zu 35 benannte Konten, davon höchstens 5 Verwaltungs-/Planungskonten |
| Gleichzeitige Nutzung | eine aktive schreibende Sitzung; parallele Bearbeitung ist nicht unterstützt |
| Planungshorizont | Wochenplanung, maximal 8 Wochen im Voraus |
| Client und Datenhaltung | Windows-Desktop-Anwendung auf einem festgelegten Pilot-PC mit lokaler SQL Server LocalDB |
| Betrieb | lokal/on-premises, ohne Cloud-Dienst und ohne extern erreichbaren Server |
| Sicherung | tägliche Sicherung der lokalen Datenbank durch den Pilotbetrieb; Wiederherstellung wird vor Pilotstart getestet |

Der Pilot-PC läuft unter Windows 10 oder Windows 11. Installation,
Initialkonfiguration, Sicherung und Wiederherstellung werden durch eine benannte
Pilot-Administration durchgeführt. Ein Wechsel zwischen mehreren Geräten oder
offline synchronisierte Clients gehören nicht zum unterstützten Betriebsmodus.

## 3. Unterstützte Rollen

Für Release 1 werden die vorhandenen Rollen auf drei unterstützte Pilotrollen
reduziert. Die Rollenbezeichnungen in Oberfläche, Anmeldung und Berechtigungen
müssen vor der Freigabe konsistent sein.

| Pilotrolle | Zuordnung im vorhandenen Rollenmodell | Rechte in Release 1 |
| --- | --- | --- |
| Pilot-Administration | `TenantAdmin` / Administrator | initial konfigurieren, Konten und Stammdaten verwalten, alle Pläne sehen, veröffentlichen und exportieren |
| Filialleitung / Planung | `StoreManager` oder `Planner` / Filialleitung oder Planer | Mitarbeitende und Schichten verwalten, Zuweisungen vornehmen, Regeln prüfen, veröffentlichen und exportieren |
| Mitarbeitende | `Employee` / Mitarbeiter | ausschließlich den eigenen veröffentlichten Plan anzeigen und exportieren |

`Personalwesen` und `Datenschutzbeauftragter` bleiben als vorhandene fachliche
Rollen sichtbar, sind aber keine separat abzunehmenden Rollen des Piloten.
Individuelle Sonderberechtigungen, rollenübergreifende Stellvertretung und
rollenabhängige Rechte über mehrere Filialen werden nach Release 1 verschoben.

## 4. Scope-Grundsätze

- **Release-1-Funktionen** müssen die Abnahmekriterien erfüllen, dauerhaft
  gespeichert sein und im unterstützten Betriebsmodus ohne manuellen Eingriff
  in Datenbank oder Quellcode funktionieren.
- **Vorschaufunktionen** dürfen im Pilot enthalten sein, müssen in Oberfläche
  und Dokumentation deutlich mit „Vorschau“ gekennzeichnet sein und dürfen
  keine Release-1-Daten verändern, ohne dass dies bestätigt und protokolliert
  wird. Für sie gibt es keine Zusage auf Vollständigkeit oder Formatstabilität.
- **Nach Release 1 verschobene Funktionen** werden nicht für den Piloten
  freigegeben. Vorhandener Code darf bestehen bleiben, darf aber nicht als
  unterstützte Pilotfunktion beworben werden.
- Demo-Daten, reine Statusmeldungen und vorbereitete Infrastruktur gelten nicht
  als Nachweis einer fertigen Release-1-Funktion.

## 5. Einordnung der vorhandenen Funktionen

Die Einordnung beschreibt den Ziel-Scope von Release 1 und zugleich die noch zu
schließenden Lücken. Insbesondere sind die vorhandene SQL-Persistenz- und
Authentifizierungsinfrastruktur derzeit noch nicht durchgängig in den
UI-Hauptablauf integriert; „Dienstplan veröffentlichen“ protokolliert aktuell
nur eine Aktion und erzeugt noch keinen dauerhaft gespeicherten,
unveränderlichen Veröffentlichungsstand.

### 5.1 Bestandteil von Release 1

| Funktion | Umfang / Freigabebedingung |
| --- | --- |
| Installation und Initialkonfiguration | installierbares Release-Paket, lokale Datenbank, ein Mandant, eine Filiale und erstes Administrationskonto |
| Anmeldung und Rollenprüfung | echte Anmeldung für die drei Pilotrollen; keine automatische Anmeldung als Demo-Administrator |
| Mitarbeiterverwaltung | Mitarbeitende anlegen und anzeigen; mindestens Name, Filiale, Abteilung, Qualifikation und Wochenstundenlimit dauerhaft speichern |
| Schichtverwaltung | Schichten anlegen, anzeigen und löschen; Zeiten, Pause, Bedarf, Abteilung und Qualifikation dauerhaft speichern |
| Dienstplanerstellung | Mitarbeitende Schichten zuweisen und die Wochenplanung in einer zentralen Übersicht anzeigen |
| Regelprüfung | harte Fehler und weiche Warnungen für die im Pilot aktivierten Regeln anzeigen; harte Fehler verhindern Veröffentlichung |
| Veröffentlichung | geprüften Plan als versionierten Veröffentlichungsstand mit Zeitpunkt und veröffentlichender Person dauerhaft speichern |
| Anzeige veröffentlichter Pläne | Filialleitung sieht den veröffentlichten Gesamtplan; Mitarbeitende sehen nur ihre eigenen veröffentlichten Schichten |
| Export veröffentlichter Pläne | unterstützte Exporte: CSV und PDF; exportiert wird ausschließlich der ausgewählte veröffentlichte Stand |
| Audit-Basis | Anmeldung, Stammdatenänderungen, Veröffentlichung und Export mit Benutzer und Zeitpunkt protokollieren |
| Neustart und Wiederherstellung | Stammdaten, Entwürfe, Zuweisungen und Veröffentlichungsstände nach Anwendungs- oder Rechnerneustart aus der lokalen Datenbank laden |

### 5.2 Als Vorschau gekennzeichnet

- Excel-Export.
- Reports zu Personalkosten, Besetzungsgrad, Überstunden und Regelverstößen.
- Forecast-Import für Umsatz und Kundenfrequenz.
- Bereitstellung von Lohnabrechnungs- und Zeiterfassungsdaten.
- DSGVO-Auskunft, Löschanfragen, Compliance-Grundlagen und erweiterte
  Audit-Ansichten.
- Verfügbarkeiten, Abwesenheiten und Schichttausch-Anträge, soweit sie in der
  Oberfläche erreichbar sind.
- Zusätzliche Planfilter außerhalb der für die Wochenplanung benötigten
  Basisfilter.

### 5.3 Nach Release 1 verschoben

- Mehrere Filialen oder Mandanten im unterstützten Betrieb.
- Gleichzeitige Bearbeitung, Konfliktauflösung, Serverbetrieb und Synchronisation
  zwischen mehreren Clients.
- Cloud-/Web-/Mobile-Zugriff und Benachrichtigungen.
- Self-Service-Prozesse für Mitarbeitende einschließlich verbindlichem
  Schichttausch-, Abwesenheits- und Verfügbarkeitsworkflow.
- Produktive Anbindung an Identity Provider, Single Sign-on oder externe
  JWT-basierte Endpunkte; Release 1 verwendet lokal verwaltete Pilotkonten.
- Produktive Schnittstellen zu Lohnabrechnung, Zeiterfassung, ERP oder
  Forecast-Systemen.
- Automatische Planung oder Optimierung des Dienstplans.
- Individuelle Berechtigungsmatrizen, Stellvertretungen und Freigabeketten mit
  mehreren Stufen.
- Rechtsverbindlicher Nachweis aller Tarif-, Arbeitszeit- oder
  Datenschutzanforderungen sowie ein allgemeiner produktiver Betrieb.

## 6. Messbare Abnahmekriterien für die Kernabläufe

Alle Kriterien werden mit einem signierten Release-Build auf einem frisch
bereitgestellten Pilot-PC geprüft. Der Abnahmedatensatz enthält 20 Mitarbeitende,
40 Schichten und mindestens 50 Zuweisungen für zwei aufeinanderfolgende Wochen.
Jeder Testfall wird mit Ergebnis, Zeitpunkt, Tester und gegebenenfalls erzeugter
Datei dokumentiert. Ein Kernablauf gilt nur als bestanden, wenn alle seine
Kriterien erfüllt sind.

### AC-01 – Anwendung installieren und initial konfigurieren

1. Ein Pilot-Administrator installiert das bereitgestellte Paket auf einem
   unterstützten, sauberen Windows-System **ohne Visual Studio** in höchstens
   15 Minuten und ohne Änderung von Quellcode oder Datenbankskripten.
2. Beim ersten Start kann der Administrator genau einen Mandanten, eine Filiale
   und das erste Administrationskonto anlegen.
3. Die Anwendung legt die lokale Datenbank einschließlich erforderlicher
   Migrationen automatisch an und zeigt einen erfolgreichen Systemstatus an.
4. Nach Abschluss der Konfiguration startet die Anwendung drei Mal
   hintereinander ohne unbehandelte Ausnahme und ohne erneut nach der
   Initialkonfiguration zu fragen.

### AC-02 – Benutzer anmelden

1. Je ein Testkonto der Rollen Pilot-Administration, Filialleitung/Planung und
   Mitarbeitende kann sich mit gültigen Anmeldedaten anmelden und sieht nur die
   für seine Rolle freigegebenen Kernfunktionen.
2. Falsche Anmeldedaten werden in 10 von 10 Versuchen abgewiesen; dabei werden
   keine geschützten Plan- oder Personaldaten angezeigt.
3. Nach Abmeldung oder Neustart ist erneut eine Anmeldung erforderlich.
4. Jede erfolgreiche und fehlgeschlagene Anmeldung wird mit Benutzerkennung,
   Ergebnis und UTC-Zeitpunkt protokolliert; Passwörter erscheinen weder im
   Audit-Log noch im Klartext in der Datenbank.

### AC-03 – Mitarbeiter und Schichten dauerhaft speichern

1. Ein Planer legt 20 Mitarbeitende und 40 Schichten über die Oberfläche an.
   Nach Schließen und erneutem Starten sind **100 %** der Datensätze und ihrer
   Pflichtfelder unverändert vorhanden.
2. Änderungen an einem Mitarbeitenden und einer Schicht sowie das Löschen einer
   Testschicht bleiben nach einem weiteren Neustart erhalten.
3. Ungültige Pflichtfelder und eine Schicht mit Ende vor Beginn werden
   reproduzierbar abgewiesen und nicht gespeichert.
4. Bei einem absichtlich ausgelösten Speicherfehler zeigt die Anwendung eine
   verständliche Fehlermeldung; es entsteht kein teilweise gespeicherter
   Datensatz.

### AC-04 – Dienstplan erstellen und prüfen

1. Ein Planer erstellt für eine Kalenderwoche mindestens 50 Zuweisungen. Nach
   erneutem Öffnen der Woche sind **100 %** der Zuweisungen vorhanden.
2. Die Planübersicht zeigt für jede Schicht Zeitraum, Bedarf, zugewiesene
   Mitarbeitende und Prüfstatus.
3. Der Abnahmedatensatz enthält mindestens je einen Fall für Unterbesetzung,
   Zeitüberschneidung, fehlende Qualifikation, Abwesenheit, überschrittenes
   Arbeitszeitlimit und verletzte Ruhezeit. Jeder aktivierte Fall erscheint
   reproduzierbar als harter Fehler oder dokumentierte Warnung.
4. Nach Behebung eines Konflikts verschwindet dessen Meldung spätestens nach
   erneuter Prüfung; konfliktfreie Schichten werden nicht fälschlich als harter
   Fehler markiert.

### AC-05 – Dienstplan veröffentlichen

1. Ein Plan mit mindestens einem harten Fehler kann in 5 von 5 Versuchen nicht
   veröffentlicht werden; die Anwendung nennt die blockierenden Fehler.
2. Ein konfliktfreier Plan kann von Pilot-Administration oder
   Filialleitung/Planung veröffentlicht werden, nicht jedoch von Mitarbeitenden.
3. Die Veröffentlichung erzeugt eine dauerhaft gespeicherte Version mit
   eindeutiger ID, Kalenderwoche, Inhalt, UTC-Zeitpunkt und veröffentlichender
   Person.
4. Spätere Änderungen am Entwurf verändern die bereits veröffentlichte Version
   nicht. Eine erneute Veröffentlichung erzeugt eine neue Version und lässt die
   vorherige Version weiterhin nachvollziehbar.

### AC-06 – Veröffentlichten Plan anzeigen und exportieren

1. Nach Veröffentlichung sieht die Filialleitung den vollständigen Stand; jedes
   der 20 Mitarbeiterkonten sieht ausschließlich seine eigenen veröffentlichten
   Schichten und keine fremden Personaldaten.
2. CSV- und PDF-Export werden für denselben ausgewählten Veröffentlichungsstand
   erzeugt. Beide enthalten Kalenderwoche, Filiale, Versionskennung,
   Schichtzeiten und zugewiesene Mitarbeitende.
3. Ein automatischer oder manueller Vergleich bestätigt, dass **100 %** der
   Schichten und Zuweisungen des veröffentlichten Stands im CSV-Export enthalten
   sind; das PDF lässt sich mit einem Standard-PDF-Reader öffnen.
4. Ein Mitarbeitendenkonto kann keinen Gesamtplan exportieren. Jeder Export wird
   mit Benutzer, Format, Veröffentlichungs-ID und UTC-Zeitpunkt protokolliert.

### AC-07 – Daten nach Neustart wiederherstellen

1. Nach ordnungsgemäßem Schließen und erneutem Start sind **100 %** der
   Mitarbeitenden, Schichten, Zuweisungen, Entwürfe und Veröffentlichungen des
   Abnahmedatensatzes vorhanden.
2. Nach einem Rechnerneustart und erneuter Anmeldung ist derselbe Datenstand
   vorhanden; die Anwendung lädt ihn ohne manuelle Datenbankaktion.
3. Eine vorab erstellte Sicherung wird auf dem Pilot-PC in höchstens 30 Minuten
   wiederhergestellt. Danach stimmen Anzahl und Stichprobeninhalt aller
   Kernobjekte mit dem Sicherungsprotokoll überein.
4. Der Wiederherstellungstest wird vor Pilotstart einmal erfolgreich
   protokolliert; ein nicht getestetes Backup gilt nicht als Freigabenachweis.

## 7. Übergreifende Freigabekriterien

Release 1 ist für den Piloten freigabefähig, wenn zusätzlich zu AC-01 bis AC-07
folgende Bedingungen erfüllt sind:

- Alle automatisierten Release-Builds und vorhandenen Unit-Tests sind grün.
- Es gibt keine offenen Fehler mit Datenverlust, unberechtigtem Datenzugriff,
  fehlerhafter Veröffentlichung oder nicht möglicher Wiederherstellung.
- Alle Vorschaufunktionen sind sichtbar als „Vorschau“ gekennzeichnet.
- Installations-, Bedien-, Sicherungs- und Wiederherstellungsanleitung liegen in
  der für den Pilotbetrieb getesteten Version vor.
- Eine benannte Person des Pilotbetriebs bestätigt den End-to-End-Test von
  Installation bis Wiederherstellung.

## 8. Bekannte Einschränkungen und Betriebsrisiken

- Release 1 ist auf einen Mandanten, eine Filiale, einen Pilot-PC und eine aktive
  schreibende Sitzung begrenzt. Gleichzeitige Änderungen können nicht sicher
  zusammengeführt werden.
- Die Desktop-Anwendung basiert auf WPF und .NET Framework 4.7.2 und ist nur für
  Windows freigegeben.
- SQL Server LocalDB ist eine lokale Pilotdatenbank, kein hochverfügbarer oder
  zentral administrierter Produktionsdatenbankdienst.
- Sicherung, Wiederherstellung, Betriebssystemschutz und physischer Zugriff auf
  den Pilot-PC liegen in der Verantwortung des Pilotbetriebs.
- Die fachlichen Prüfregeln unterstützen die Planung, ersetzen aber keine
  rechtliche, tarifliche oder betriebliche Prüfung.
- Vorschau-Exporte und Vorschau-Integrationen können unvollständig sein und
  dürfen nicht ungeprüft für Lohnabrechnung, Zeiterfassung oder rechtliche
  Nachweise verwendet werden.
- Der Pilot bietet keine garantierte Hochverfügbarkeit, keine zugesicherten
  Antwortzeiten und keinen 24/7-Support.
- Vorhandene Demo-Daten und Demo-Konten dürfen im signierten Pilot-Build nicht
  aktiv sein.

## 9. Erfolgsmessung und Abschluss des Piloten

Der Pilot läuft über mindestens vier vollständige Planungswochen. Er gilt als
erfolgreich, wenn in diesem Zeitraum jeder Wochenplan veröffentlicht und von den
betroffenen Mitarbeitenden angezeigt werden kann, kein Datenverlust auftritt,
kein unberechtigter Zugriff bekannt wird und mindestens eine Wiederherstellung
erfolgreich nachgewiesen ist. Zusätzlich werden Anzahl und Schwere der Fehler,
Zeitaufwand für die Planerstellung sowie Rückmeldungen der Pilotrollen erfasst.

Ein erfolgreicher Pilot ist **keine automatische Produktivfreigabe**. Die
Entscheidung über ein späteres produktives Release erfordert einen eigenen
Scope, insbesondere für Sicherheit, Datenschutz, Betrieb, Support,
Mehrbenutzerfähigkeit und produktive Integrationen.
