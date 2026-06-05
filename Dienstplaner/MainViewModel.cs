using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using Dienstplaner.Helpers;
using Dienstplaner.Infrastructure.Services;
using Dienstplaner.Models;
using Dienstplaner.Services;

namespace Dienstplaner.ViewModels
{
    public class MainViewModel : INotifyPropertyChanged, IDataErrorInfo
    {
        private readonly ZuweisungsService _service;
        private readonly DienstplanDataService _dataService;
        private readonly DienstplanExportService _exportService;
        private readonly ReportingService _reportingService;
        private readonly IntegrationsService _integrationsService;
        private readonly ForecastImportService _forecastImportService;
        private readonly DsgvoService _dsgvoService;
        private readonly RollenService _rollenService;
        private readonly AuditService _auditService;
        private string _statusNachricht;

        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; set; }
        public ObservableCollection<Schicht> SchichtListe { get; set; }
        public ObservableCollection<ReportKennzahl> ReportListe { get; set; }
        public ObservableCollection<UmsatzForecast> ForecastListe { get; set; }
        public ObservableCollection<PayrollRecord> LohnabrechnungListe { get; set; }
        public ObservableCollection<TimeTrackingRecord> ZeiterfassungListe { get; set; }
        public ObservableCollection<Availability> Verfuegbarkeiten { get; set; }
        public ObservableCollection<Absence> Abwesenheiten { get; set; }
        public ObservableCollection<AuditLogEintrag> AuditLog { get; private set; }
        public ObservableCollection<string> ZuweisungsFehler { get; private set; }
        public ObservableCollection<string> ZuweisungsWarnungen { get; private set; }

        public ObservableCollection<Mitarbeiter> MitarbeiterView { get { return MitarbeiterListe; } }
        public ObservableCollection<Schicht> SchichtView { get { return SchichtListe; } }

        public Mitarbeiter AusgewaehlterMitarbeiter { get; set; }
        public Schicht AusgewaehlteSchicht { get; set; }
        public Availability AusgewaehlteVerfuegbarkeit { get; set; }
        public Absence AusgewaehlteAbwesenheit { get; set; }
        public ShiftSwapRequest AusgewaehlterTauschAntrag { get; set; }

        public MandantKontext AktuellerKontext { get; set; }
        public BenutzerKontext AktuellerBenutzer { get; set; }
        public ComplianceRichtlinie ComplianceRichtlinie { get; }

        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }
        public decimal NeueMitarbeiterSollstunden { get; set; } = 40;
        public decimal NeuerMitarbeiterStundenlohn { get; set; } = 15;

        public string NeueSchichtName { get; set; }
        public string NeueSchichtAbteilung { get; set; }
        public string NeueSchichtWochentag { get; set; }
        public int NeueSchichtStoreId { get; set; } = 1;
        public int NeueSchichtDepartmentId { get; set; } = 1;
        public int NeueSchichtRoleId { get; set; } = 1;
        public DateTime NeueSchichtDatum { get; set; } = DateTime.Today;
        public string NeueSchichtStartzeit { get; set; } = "08:00";
        public string NeueSchichtEndzeit { get; set; } = "16:00";
        public int NeueSchichtPauseMinuten { get; set; } = 30;
        public int NeueSchichtKapazitaet { get; set; } = 2;
        public decimal NeueSchichtPausenstunden { get; set; } = 0.5m;
        public decimal NeueSchichtZuschlagsstunden { get; set; }
        public string ForecastImportPfad { get; set; }

        public string FilterFiliale { get; set; }
        public string FilterAbteilung { get; set; }
        public string FilterWoche { get; set; }
        public string FilterRolle { get; set; }
        public Mitarbeiter FilterMitarbeiter { get; set; }

        public string StatusNachricht 
        { 
            get { return _statusNachricht; }
            set 
            { 
                _statusNachricht = value;
                OnPropertyChanged(nameof(StatusNachricht));
            }
        }
        
        public string DsgvoExportText { get; set; }

        public string MitarbeiterFehlerNachricht { get; set; }
        public string SchichtFehlerNachricht { get; set; }

        public int BesetzungSoll
        {
            get { return SchichtListe.Sum(s => s.BenoetigteMitarbeiter); }
        }

        public int BesetzungIst
        {
            get { return SchichtListe.Sum(s => s.MitarbeiterNamen.Count); }
        }

        public int BesetzungsDifferenz
        {
            get { return BesetzungIst - BesetzungSoll; }
        }

        public int KonfliktAnzahl
        {
            get { return SchichtListe.Count(s => !s.IstVoll || s.MitarbeiterNamen.Count > s.BenoetigteMitarbeiter); }
        }

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }
        public ICommand SchichtLoeschenCommand { get; }
        public ICommand DienstplanVeroeffentlichenCommand { get; }
        public ICommand DsgvoAuskunftCommand { get; }
        public ICommand DsgvoLoeschenCommand { get; }
        public ICommand CsvExportCommand { get; }
        public ICommand ExcelExportCommand { get; }
        public ICommand PdfExportCommand { get; }
        public ICommand ReportsAktualisierenCommand { get; }
        public ICommand IntegrationenAktualisierenCommand { get; }
        public ICommand ForecastImportCommand { get; }

        public string Error { get { return null; } }

        public event PropertyChangedEventHandler PropertyChanged;

        public string this[string columnName]
        {
            get { return ValidiereProperty(columnName); }
        }

        public MainViewModel()
            : this(null)
        {
        }

        public MainViewModel(DienstplanDataService dataService)
        {
            _dataService = dataService;
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>(dataService != null ? dataService.LadeMitarbeiter() : Enumerable.Empty<Mitarbeiter>());
            SchichtListe = new ObservableCollection<Schicht>(dataService != null ? dataService.LadeSchichten() : Enumerable.Empty<Schicht>());
            ReportListe = new ObservableCollection<ReportKennzahl>();
            ForecastListe = new ObservableCollection<UmsatzForecast>();
            LohnabrechnungListe = new ObservableCollection<PayrollRecord>();
            ZeiterfassungListe = new ObservableCollection<TimeTrackingRecord>();
            Verfuegbarkeiten = new ObservableCollection<Availability>();
            Abwesenheiten = new ObservableCollection<Absence>();
            ZuweisungsFehler = new ObservableCollection<string>();
            ZuweisungsWarnungen = new ObservableCollection<string>();


            AktuellerKontext = new MandantKontext
            {
                MandantId = 1,
                MandantName = "Standardmandant",
                FilialeId = 1,
                FilialeName = "Zentrale",
                Rolle = BenutzerRolle.Personalwesen
            };

            AktuellerBenutzer = BenutzerKontext.StandardAdmin();
            ComplianceRichtlinie = new ComplianceRichtlinie();

            _rollenService = new RollenService();
            _auditService = new AuditService(new DataProtectionService());
            _service = new ZuweisungsService(_auditService, _rollenService);
            _exportService = new DienstplanExportService();
            _reportingService = new ReportingService();
            _integrationsService = new IntegrationsService();
            _forecastImportService = new ForecastImportService();
            _dsgvoService = new DsgvoService(_rollenService, _auditService);
            AuditLog = _auditService.Eintraege;

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);
            SchichtLoeschenCommand = new RelayCommand(SchichtLoeschen);
            DienstplanVeroeffentlichenCommand = new RelayCommand(DienstplanVeroeffentlichen);
            DsgvoAuskunftCommand = new RelayCommand(DsgvoAuskunftErstellen);
            DsgvoLoeschenCommand = new RelayCommand(DsgvoLoeschanfrageBearbeiten);
            CsvExportCommand = new RelayCommand(o => Exportiere(ExportFormat.Csv));
            ExcelExportCommand = new RelayCommand(o => Exportiere(ExportFormat.Excel));
            PdfExportCommand = new RelayCommand(o => Exportiere(ExportFormat.Pdf));
            ReportsAktualisierenCommand = new RelayCommand(AktualisiereReports);
            IntegrationenAktualisierenCommand = new RelayCommand(AktualisiereIntegrationen);
            ForecastImportCommand = new RelayCommand(ImportiereForecast);

            AktualisiereReports(null);
            AktualisiereIntegrationen(null);
        }

        private bool FilterSchicht(object item)
        {
            var schicht = item as Schicht;
            if (schicht == null) return false;

            if (!string.IsNullOrEmpty(FilterFiliale) && !schicht.FilialeName.Contains(FilterFiliale))
                return false;

            if (!string.IsNullOrEmpty(FilterAbteilung) && !schicht.Abteilung.Contains(FilterAbteilung))
                return false;

            return true;
        }

        private void AddMitarbeiter(object obj)
        {
            string fehler;
            if (!IstMitarbeiterGueltig(out fehler))
            {
                SetStatus(NormalisiereValidierungsfehler(fehler));
                return;
            }

            FuehreMitRollenpruefungAus("Mitarbeiter erstellen", () =>
            {
                var neuerMitarbeiter = _dataService != null
                    ? _dataService.MitarbeiterHinzufuegen(NeuerMitarbeiterName.Trim(), NeueMitarbeiterAbteilung.Trim(), NeuerMitarbeiterQualifikation.Trim(), 48)
                    : new Mitarbeiter
                    {
                        Id = NaechsteId(MitarbeiterListe.Select(m => m.Id)),
                        MandantId = AktuellerKontext.MandantId,
                        FilialeId = AktuellerKontext.FilialeId,
                        Name = NeuerMitarbeiterName.Trim(),
                        Abteilung = NeueMitarbeiterAbteilung.Trim(),
                        DepartmentId = ParseIntOrZero(NeueMitarbeiterAbteilung),
                        Qualifikation = NeuerMitarbeiterQualifikation.Trim(),
                        SollstundenProWoche = NeueMitarbeiterSollstunden,
                        WochenstundenLimit = 48,
                        Stundenlohn = NeuerMitarbeiterStundenlohn,
                        IstAktiv = true
                    };
                MitarbeiterListe.Add(neuerMitarbeiter);

                NeuerMitarbeiterName = string.Empty;
                NeueMitarbeiterAbteilung = string.Empty;
                NeuerMitarbeiterQualifikation = string.Empty;
                OnPropertyChanged(nameof(NeuerMitarbeiterName));
                OnPropertyChanged(nameof(NeueMitarbeiterAbteilung));
                OnPropertyChanged(nameof(NeuerMitarbeiterQualifikation));
                SetStatus("Mitarbeiter hinzugefügt");
            });
        }

        private void AddSchicht(object obj)
        {
            string fehler;
            int kapazitaet;
            TimeSpan startzeit;
            TimeSpan endzeit;
            if (!IstSchichtGueltig(out fehler, out kapazitaet, out startzeit, out endzeit))
            {
                SetStatus(NormalisiereValidierungsfehler(fehler));
                return;
            }

            FuehreMitRollenpruefungAus("Schicht erstellen", () =>
            {
                var datum = NeueSchichtDatum.Date;
                var neueSchicht = _dataService != null
                    ? _dataService.SchichtHinzufuegen(NeueSchichtName.Trim(), NeueSchichtAbteilung.Trim(), NeueSchichtWochentag.Trim(), datum.Add(startzeit), datum.Add(endzeit), kapazitaet, null)
                    : new Schicht
                    {
                        Id = NaechsteId(SchichtListe.Select(s => s.Id)),
                        MandantId = AktuellerKontext.MandantId,
                        FilialeId = AktuellerKontext.FilialeId,
                        FilialeName = AktuellerKontext.FilialeName,
                        StoreId = NeueSchichtStoreId,
                        DepartmentId = NeueSchichtDepartmentId,
                        RoleId = NeueSchichtRoleId,
                        Name = NeueSchichtName.Trim(),
                        Abteilung = NeueSchichtAbteilung.Trim(),
                        Rolle = NeueSchichtAbteilung.Trim(),
                        Wochentag = NeueSchichtWochentag.Trim(),
                        BenoetigteMitarbeiter = kapazitaet,
                        Pausenstunden = NeueSchichtPausenstunden,
                        Zuschlagsstunden = NeueSchichtZuschlagsstunden,
                        Start = datum.Add(startzeit),
                        Ende = datum.Add(endzeit)
                    };
                SchichtListe.Add(neueSchicht);

                NeueSchichtName = string.Empty;
                NeueSchichtAbteilung = string.Empty;
                NeueSchichtWochentag = string.Empty;
                NeueSchichtKapazitaet = 2;
                OnPropertyChanged(nameof(NeueSchichtName));
                OnPropertyChanged(nameof(NeueSchichtAbteilung));
                OnPropertyChanged(nameof(NeueSchichtWochentag));
                OnPropertyChanged(nameof(NeueSchichtKapazitaet));
                SetStatus("Schicht hinzugefügt");
            });
        }

        private void Zuweisen(object obj)
        {
            ZuweisungsFehler.Clear();
            ZuweisungsWarnungen.Clear();

            FuehreMitRollenpruefungAus("Dienstplan ändern", () =>
            {
                var ergebnis = _service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht, AktuellerBenutzer);
                if (string.Equals(ergebnis, "Zuweisung erfolgreich", StringComparison.Ordinal) && _dataService != null)
                {
                    ergebnis = _dataService.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);
                    if (!string.Equals(ergebnis, "Zuweisung erfolgreich", StringComparison.Ordinal))
                        RueckgaengigMachen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);
                }

                if (!string.Equals(ergebnis, "Zuweisung erfolgreich", StringComparison.Ordinal))
                    ZuweisungsFehler.Add(ergebnis);

                SetStatus(ergebnis);
            });
        }

        private static void RueckgaengigMachen(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            mitarbeiter.Schichten.Remove(schicht);
            mitarbeiter.AktuelleWochenstunden -= (int)schicht.NettoDauerInStunden;
            schicht.MitarbeiterNamen.Remove(mitarbeiter.Name);
            schicht.MitarbeiterIds.Remove(mitarbeiter.Id);
        }

        private void SchichtLoeschen(object obj)
        {
            FuehreMitRollenpruefungAus("Schicht löschen", () =>
            {
                if (AusgewaehlteSchicht == null)
                {
                    SetStatus("Keine Schicht zum Löschen ausgewählt");
                    return;
                }

                var schicht = AusgewaehlteSchicht;
                var alteWerte = schicht.ToString();
                if (_dataService != null)
                    _dataService.SchichtLoeschen(schicht);
                foreach (var mitarbeiter in MitarbeiterListe)
                    mitarbeiter.Schichten.Remove(schicht);

                SchichtListe.Remove(schicht);
                _auditService.Protokolliere(AuditAction.DienstplanGeloescht, "Schicht", schicht.Id, AktuellerBenutzer, alteWerte, string.Empty, "Dienstplan-Schicht gelöscht");
                SetStatus("Schicht gelöscht");
            });
        }

        private void DienstplanVeroeffentlichen(object obj)
        {
            FuehreMitRollenpruefungAus("Dienstplan veröffentlichen", () =>
            {
                var neueWerte = $"Schichten={SchichtListe.Count};Mitarbeiter={MitarbeiterListe.Count}";
                _auditService.Protokolliere(AuditAction.DienstplanVeroeffentlicht, "Dienstplan", 0, AktuellerBenutzer, string.Empty, neueWerte, "Dienstplan veröffentlicht");
                SetStatus("Dienstplan veröffentlicht");
            });
        }

        private void DsgvoAuskunftErstellen(object obj)
        {
            try
            {
                DsgvoExportText = _dsgvoService.ExportierePersonenDaten(AusgewaehlterMitarbeiter, SchichtListe, AktuellerBenutzer);
                OnPropertyChanged(nameof(DsgvoExportText));
                SetStatus("DSGVO-Auskunft erstellt");
            }
            catch (UnauthorizedAccessException ex)
            {
                SetStatus(ex.Message);
            }
        }

        private void DsgvoLoeschanfrageBearbeiten(object obj)
        {
            try
            {
                SetStatus(_dsgvoService.BearbeiteLoeschanfrage(AusgewaehlterMitarbeiter, SchichtListe, AktuellerBenutzer));
                OnPropertyChanged(nameof(MitarbeiterView));
                OnPropertyChanged(nameof(SchichtView));
            }
            catch (UnauthorizedAccessException ex)
            {
                SetStatus(ex.Message);
            }
        }

        private void Exportiere(ExportFormat format)
        {
            try
            {
                _exportService.ExportiereDienstplan(SchichtListe, AktuellerKontext, format, "Exporte");
                SetStatus($"Export als {format} erfolgreich");
            }
            catch (Exception ex)
            {
                SetStatus($"Export fehlgeschlagen: {ex.Message}");
            }
        }

        private void AktualisiereReports(object obj)
        {
            try
            {
                var reports = _reportingService.ErstelleReports(MitarbeiterListe, SchichtListe);
                ReportListe.Clear();
                foreach (var report in reports)
                    ReportListe.Add(report);
                SetStatus("Reports aktualisiert");
            }
            catch (Exception ex)
            {
                SetStatus($"Report-Fehler: {ex.Message}");
            }
        }

        private void AktualisiereIntegrationen(object obj)
        {
            try
            {
                LohnabrechnungListe.Clear();
                foreach (var eintrag in _integrationsService.ErstelleLohnabrechnung(MitarbeiterListe))
                    LohnabrechnungListe.Add(eintrag);

                ZeiterfassungListe.Clear();
                foreach (var eintrag in _integrationsService.ErstelleZeiterfassung(MitarbeiterListe))
                    ZeiterfassungListe.Add(eintrag);
                SetStatus("Integrationen aktualisiert");
            }
            catch (Exception ex)
            {
                SetStatus($"Integrations-Fehler: {ex.Message}");
            }
        }

        private void ImportiereForecast(object obj)
        {
            try
            {
                if (string.IsNullOrEmpty(ForecastImportPfad))
                {
                    SetStatus("Bitte geben Sie einen Import-Pfad an");
                    return;
                }

                var forecasts = _forecastImportService.ImportiereCsv(ForecastImportPfad);
                ForecastListe.Clear();
                foreach (var forecast in forecasts)
                    ForecastListe.Add(forecast);
                SetStatus($"{forecasts.Count} Forecast-Einträge importiert");
            }
            catch (Exception ex)
            {
                SetStatus($"Import-Fehler: {ex.Message}");
            }
        }

        private void FuehreMitRollenpruefungAus(string aktion, Action aktionAusfuehren)
        {
            try
            {
                _rollenService.StellePersonenDatenZugriffSicher(AktuellerBenutzer, aktion);
                aktionAusfuehren();
            }
            catch (UnauthorizedAccessException ex)
            {
                SetStatus(ex.Message);
            }
        }

        private string ValidiereProperty(string propertyName)
        {
            switch (propertyName)
            {
                case nameof(NeuerMitarbeiterName):
                    return PflichtfeldFehler(NeuerMitarbeiterName, "Name");
                case nameof(NeueMitarbeiterAbteilung):
                    return PflichtfeldFehler(NeueMitarbeiterAbteilung, "Abteilung");
                case nameof(NeuerMitarbeiterQualifikation):
                    return PflichtfeldFehler(NeuerMitarbeiterQualifikation, "Qualifikation");
                case nameof(NeueSchichtName):
                    return PflichtfeldFehler(NeueSchichtName, "Schichtname");
                case nameof(NeueSchichtAbteilung):
                    return PflichtfeldFehler(NeueSchichtAbteilung, "Abteilung");
                case nameof(NeueSchichtWochentag):
                    return PflichtfeldFehler(NeueSchichtWochentag, "Wochentag");
                case nameof(NeueSchichtKapazitaet):
                    return ValidiereKapazitaet(NeueSchichtKapazitaet);
                case nameof(NeueSchichtStartzeit):
                    return ValidiereUhrzeit(NeueSchichtStartzeit, "Startzeit");
                case nameof(NeueSchichtEndzeit):
                    return ValidiereEndzeit();
                default:
                    return string.Empty;
            }
        }

        private bool IstMitarbeiterGueltig(out string fehler)
        {
            fehler = ErsterFehler(
                ValidiereProperty(nameof(NeuerMitarbeiterName)),
                ValidiereProperty(nameof(NeueMitarbeiterAbteilung)),
                ValidiereProperty(nameof(NeuerMitarbeiterQualifikation)));

            if (!string.IsNullOrEmpty(fehler))
                fehler = "Mitarbeiter kann nicht gespeichert werden: " + fehler;

            return string.IsNullOrEmpty(fehler);
        }

        private bool IstSchichtGueltig(out string fehler)
        {
            int kapazitaet;
            TimeSpan startzeit;
            TimeSpan endzeit;
            return IstSchichtGueltig(out fehler, out kapazitaet, out startzeit, out endzeit);
        }

        private bool IstSchichtGueltig(out string fehler, out int kapazitaet, out TimeSpan startzeit, out TimeSpan endzeit)
        {
            int.TryParse(NeueSchichtKapazitaet.ToString(), out kapazitaet);
            TimeSpan.TryParse(NeueSchichtStartzeit, out startzeit);
            TimeSpan.TryParse(NeueSchichtEndzeit, out endzeit);

            fehler = ErsterFehler(
                ValidiereProperty(nameof(NeueSchichtName)),
                ValidiereProperty(nameof(NeueSchichtAbteilung)),
                ValidiereProperty(nameof(NeueSchichtWochentag)),
                ValidiereProperty(nameof(NeueSchichtKapazitaet)),
                ValidiereProperty(nameof(NeueSchichtStartzeit)),
                ValidiereProperty(nameof(NeueSchichtEndzeit)));

            if (!string.IsNullOrEmpty(fehler))
                fehler = "Schicht kann nicht gespeichert werden: " + fehler;

            return string.IsNullOrEmpty(fehler);
        }

        private static string NormalisiereValidierungsfehler(string fehler)
        {
            if (fehler.Contains("Name ist ein Pflichtfeld")) return "Mitarbeitername ist erforderlich";
            if (fehler.Contains("Abteilung ist ein Pflichtfeld") && fehler.Contains("Mitarbeiter")) return "Mitarbeiterabteilung ist erforderlich";
            if (fehler.Contains("Wochentag ist ein Pflichtfeld")) return "Schichtwochentag ist erforderlich";
            if (fehler.Contains("Kapazität muss mindestens 1 sein")) return "Schichtkapazität muss größer als 0 sein";
            return fehler;
        }

        private static string PflichtfeldFehler(string wert, string feldname)
        {
            return string.IsNullOrWhiteSpace(wert) ? feldname + " ist ein Pflichtfeld." : string.Empty;
        }

        private static string ValidiereKapazitaet(int wert)
        {
            if (wert < 1)
                return "Kapazität muss mindestens 1 sein.";

            return string.Empty;
        }

        private static string ValidiereUhrzeit(string wert, string feldname)
        {
            TimeSpan zeit;

            if (string.IsNullOrWhiteSpace(wert))
                return feldname + " ist ein Pflichtfeld.";

            if (!TimeSpan.TryParse(wert, out zeit))
                return feldname + " muss im Format HH:mm eingegeben werden.";

            if (zeit < TimeSpan.Zero || zeit >= TimeSpan.FromDays(1))
                return feldname + " muss zwischen 00:00 und 23:59 liegen.";

            return string.Empty;
        }

        private string ValidiereEndzeit()
        {
            TimeSpan startzeit;
            TimeSpan endzeit;
            string endzeitFehler = ValidiereUhrzeit(NeueSchichtEndzeit, "Endzeit");

            if (!string.IsNullOrEmpty(endzeitFehler))
                return endzeitFehler;

            if (!TimeSpan.TryParse(NeueSchichtStartzeit, out startzeit) || !TimeSpan.TryParse(NeueSchichtEndzeit, out endzeit))
                return string.Empty;

            if (endzeit <= startzeit)
                return "Endzeit muss nach der Startzeit liegen.";

            return string.Empty;
        }

        private static string ErsterFehler(params string[] fehler)
        {
            foreach (string einzelnerFehler in fehler)
            {
                if (!string.IsNullOrEmpty(einzelnerFehler))
                    return einzelnerFehler;
            }

            return string.Empty;
        }

        private void OnPropertyChanged([CallerMemberName] string n = null)
        {
            var handler = PropertyChanged;
            if (handler != null)
                handler(this, new PropertyChangedEventArgs(n));
        }
    }
}
