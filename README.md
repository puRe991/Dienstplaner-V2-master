# Dienstplaner

Professionelle Desktop-Anwendung zur Erstellung, Prüfung und Auswertung von
Dienstplänen. Der Dienstplaner unterstützt Verantwortliche dabei, Mitarbeitende
regelkonform Schichten zuzuweisen, Planungsdaten auszuwerten und relevante
Informationen sicher zu exportieren.

> **Projektstatus:** Der aktuelle Stand ist ein funktionsfähiger Prototyp mit
> SQL-Server-Persistenzpfad. Vor einem produktiven Einsatz sollten insbesondere
> Authentifizierung, Berechtigungskonzept und Datenschutzprozesse an
> die eigene Umgebung angepasst und geprüft werden.

## Inhaltsverzeichnis

- [Funktionsumfang](#funktionsumfang)
- [Technologie](#technologie)
- [Voraussetzungen](#voraussetzungen)
- [Schnellstart](#schnellstart)
- [Tests und Qualitätssicherung](#tests-und-qualitätssicherung)
- [Projektstruktur](#projektstruktur)
- [Konfiguration und Datenhaltung](#konfiguration-und-datenhaltung)
- [Fachliche Planungsregeln](#fachliche-planungsregeln)
- [Mitwirken](#mitwirken)
- [Lizenz](#lizenz)

## Funktionsumfang

- **Mitarbeiter- und Schichtplanung:** Mitarbeitende und Schichten anlegen sowie
  Mitarbeitende Schichten zuweisen.
- **Regelbasierte Validierung:** Harte Fehler und weiche Warnungen für
  Kapazität, Qualifikation, Arbeitszeit, Ruhezeit, Pausen, Verfügbarkeit,
  Abwesenheit und Zeitkonflikte.
- **Planungsübersicht:** Schichten, Besetzung und Warnstatus in einer zentralen
  WPF-Oberfläche darstellen.
- **Forecast-Import:** Umsatz- und Kundenfrequenzdaten aus CSV-Dateien
  importieren.
- **Reporting und Integrationen:** Kennzahlen sowie Daten für Lohnabrechnung und
  Zeiterfassung erzeugen.
- **Geschützte Exporte:** Dienstpläne abhängig von Mandant, Filiale, Rolle und
  Exportformat als CSV, Excel oder PDF ausgeben.
- **DSGVO- und Audit-Funktionen:** Personendatenauskunft, Löschanfragen,
  Compliance-Grundlagen und Audit-Einträge verwalten.
- **Antragsprozesse:** Verfügbarkeiten, Abwesenheiten und Schichttausch-Anfragen
  fachlich abbilden.

## Technologie

| Bereich | Technologie |
| --- | --- |
| Anwendung | C#, WPF, XAML |
| Architektur | MVVM-orientierte Desktop-Anwendung |
| Zielplattform | .NET Framework 4.7.2, Any CPU |
| Tests | NUnit 3, Microsoft.NET.Test.Sdk, NUnit3TestAdapter |
| CI | GitHub Actions mit NuGet, MSBuild, NUnit und CodeQL |

## Voraussetzungen

Für Entwicklung und Ausführung werden empfohlen:

- Windows 10 oder Windows 11
- Visual Studio 2019 oder neuer mit der Workload **.NET-Desktopentwicklung**
- .NET Framework 4.7.2 Developer Pack
- Git
- Optional: SQL Server LocalDB für die in `App.config` vorbereitete
  Verbindungszeichenfolge

> WPF und .NET Framework 4.7.2 sind Windows-Technologien. Build, Tests und
> Anwendungsausführung sollten deshalb in einer Windows-Umgebung erfolgen.

## Schnellstart

### 1. Repository klonen

```powershell
git clone <REPOSITORY-URL>
cd Dienstplaner-V2-master
```

### 2. Abhängigkeiten wiederherstellen

In einer **Developer PowerShell for Visual Studio**:

```powershell
nuget restore Dienstplaner.sln
```

Alternativ stellt Visual Studio die NuGet-Pakete beim Öffnen und Erstellen der
Projektmappe automatisch wieder her.

### 3. Projektmappe erstellen

```powershell
msbuild Dienstplaner.sln /m /p:Configuration=Release /p:Platform="Any CPU"
```

### 4. Anwendung starten

- `Dienstplaner.sln` in Visual Studio öffnen.
- Das Projekt **Dienstplaner** als Startprojekt auswählen.
- Mit `F5` starten.

Beim Start verbindet sich die Anwendung mit der in `App.config` hinterlegten
Datenbank, führt ausstehende Migrationen aus und lädt die persistierten
Planungsdaten.

## Tests und Qualitätssicherung

Die Unit-Tests prüfen insbesondere die Zuweisungsregeln und die Validierung im
Haupt-ViewModel.

```powershell
dotnet test Dienstplaner.Tests\Dienstplaner.Tests.csproj `
  --configuration Release `
  --framework net472
```

Für eine Prüfung analog zur CI-Pipeline:

```powershell
nuget restore Dienstplaner.sln
msbuild Dienstplaner.sln /m /p:Configuration=Release `
  /p:Platform="Any CPU" /p:TreatWarningsAsErrors=true
dotnet test Dienstplaner.Tests\Dienstplaner.Tests.csproj `
  --configuration Release --no-build --framework net472
```

Die GitHub-Actions-Pipeline wird bei Pull Requests sowie Pushes auf `main` oder
`master` ausgeführt und umfasst Restore, Release-Build, Unit-Tests und
CodeQL-Analyse.

## Projektstruktur

```text
.
├── .github/workflows/ci.yml       # Automatisierte Qualitätssicherung
├── Dienstplaner.sln               # Visual-Studio-Projektmappe
├── Dienstplaner/                  # WPF-Anwendung und Fachlogik
│   ├── MainWindow.xaml            # Benutzeroberfläche
│   ├── MainViewModel.cs           # UI-Zustand, Commands und Bindings
│   ├── PlanningRules.cs           # Fachliche Regeln der Schichtzuweisung
│   ├── ZuweisungsService.cs       # Ausführung und Prüfung von Zuweisungen
│   ├── Services/                  # Export-, Forecast-, Reporting- und Integrationsdienste
│   └── Infrastructure/            # Vorbereitete SQL-Server-Persistenzschicht
└── Dienstplaner.Tests/            # NUnit-Tests und Testdaten
```

## Konfiguration und Datenhaltung

Die Anwendung arbeitet im UI-Ablauf mit der vorbereiteten
SQL-Server-Infrastruktur. Die standardmäßige LocalDB-Verbindung ist in
`Dienstplaner/App.config` hinterlegt:

```xml
Data Source=(localdb)\MSSQLLocalDB;Initial Catalog=Dienstplaner;Integrated Security=True
```

Für produktive Umgebungen sollte die Verbindungszeichenfolge außerhalb des
Quellcodes verwaltet werden. Zugangsdaten, Tokens und andere Geheimnisse dürfen
nicht in Git eingecheckt werden.

Forecast-Dateien erwartet die Anwendung als semikolongetrennte CSV-Dateien mit
folgendem Aufbau:

```text
FilialeId;Filiale;Datum;Umsatz;Kunden
```

## Fachliche Planungsregeln

Der Zuweisungsprozess wertet mehrere Regeln aus. Dazu gehören unter anderem:

- gültige Auswahl und aktive Mitarbeitende,
- verfügbare Schichtkapazität,
- passende Qualifikation sowie Filial- und Abteilungszuordnung,
- maximale Wochen- und Tagesarbeitszeit,
- Einhaltung von Ruhezeiten und Pausenpflichten,
- Ausschluss zeitlicher Überschneidungen,
- Berücksichtigung von Verfügbarkeiten und Abwesenheiten.

Fehler verhindern eine Zuweisung; Warnungen werden separat angezeigt und
ermöglichen eine bewusste fachliche Entscheidung.

## Mitwirken

Beiträge sind willkommen. Bitte nutze für Änderungen folgenden Ablauf:

1. Einen Branch von `main` oder `master` erstellen.
2. Änderungen klein, nachvollziehbar und fachlich fokussiert umsetzen.
3. Bestehende Tests ausführen und neue Logik durch passende Tests absichern.
4. Einen Pull Request mit einer klaren Beschreibung von Problem, Lösung und
   Testergebnissen eröffnen.

Bei Fehlerberichten helfen reproduzierbare Schritte, erwartetes und
tatsächliches Verhalten sowie Angaben zur Windows- und Visual-Studio-Version.

## Lizenz

Für dieses Repository ist derzeit keine Lizenzdatei hinterlegt. Ohne
ausdrückliche Lizenz bleiben alle Rechte bei den jeweiligen Rechteinhabern. Vor
Nutzung, Weitergabe oder produktivem Einsatz sollten die Lizenzbedingungen mit
den Projektverantwortlichen geklärt werden.
