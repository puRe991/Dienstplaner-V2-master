using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using Dienstplaner.Helpers;
using Dienstplaner.Models;
using Dienstplaner.Services;

namespace Dienstplaner.ViewModels
{
    public class MainViewModel : INotifyPropertyChanged, IDataErrorInfo
    {
        private readonly ZuweisungsService _service;
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
        public ICommand CsvExportCommand { get; }
        public ICommand ExcelExportCommand { get; }
        public ICommand PdfExportCommand { get; }
        public ICommand ReportsAktualisierenCommand { get; }
        public ICommand IntegrationenAktualisierenCommand { get; }
        public ICommand ForecastImportCommand { get; }

        public string Error { get { return null; } }

        public string this[string columnName]
        {
            get { return ValidiereProperty(columnName); }
        }

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();
            ReportListe = new ObservableCollection<ReportKennzahl>();
            ForecastListe = new ObservableCollection<UmsatzForecast>();
            LohnabrechnungListe = new ObservableCollection<PayrollRecord>();
            ZeiterfassungListe = new ObservableCollection<TimeTrackingRecord>();
            Verfuegbarkeiten = new ObservableCollection<Availability>();
            Abwesenheiten = new ObservableCollection<Absence>();

            AktuellerKontext = new MandantKontext
            {
                MandantId = 1,
                MandantName = "DemoMandant",
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

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter, CanAddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht, CanAddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);
            CsvExportCommand = new RelayCommand(o => Exportiere(ExportFormat.Csv));
            ExcelExportCommand = new RelayCommand(o => Exportiere(ExportFormat.Excel));
            PdfExportCommand = new RelayCommand(o => Exportiere(ExportFormat.Pdf));
            ReportsAktualisierenCommand = new RelayCommand(AktualisiereReports);
            IntegrationenAktualisierenCommand = new RelayCommand(AktualisiereIntegrationen);
            ForecastImportCommand = new RelayCommand(ImportiereForecast);

            Seed();
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

        private bool CanAddMitarbeiter(object obj)
        {
            return !string.IsNullOrWhiteSpace(NeuerMitarbeiterName)
                && !string.IsNullOrWhiteSpace(NeueMitarbeiterAbteilung)
                && !string.IsNullOrWhiteSpace(NeuerMitarbeiterQualifikation);
        }

        private bool CanAddSchicht(object obj)
        {
            return !string.IsNullOrWhiteSpace(NeueSchichtName)
                && !string.IsNullOrWhiteSpace(NeueSchichtAbteilung)
                && !string.IsNullOrWhiteSpace(NeueSchichtWochentag)
                && NeueSchichtKapazitaet > 0;
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
                var neuerMitarbeiter = new Mitarbeiter
                {
                    Id = MitarbeiterListe.Count + 1,
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
                SetStatus("Mitarbeiter hinzugefügt");
            });
        }

        private void AddSchicht(object obj)
        {
            string fehler;
            if (!IstSchichtGueltig(out fehler))
            {
                SetStatus(NormalisiereValidierungsfehler(fehler));
                return;
            }

            FuehreMitRollenpruefungAus("Schicht erstellen", () =>
            {
                var neueSchicht = new Schicht
                {
                    Id = SchichtListe.Count + 1,
                    MandantId = AktuellerKontext.MandantId,
                    FilialeId = AktuellerKontext.FilialeId,
                    FilialeName = AktuellerKontext.FilialeName,
                    Name = NeueSchichtName.Trim(),
                    Abteilung = NeueSchichtAbteilung.Trim(),
                    Rolle = NeueSchichtAbteilung.Trim(),
                    Wochentag = NeueSchichtWochentag.Trim(),
                    BenoetigteMitarbeiter = NeueSchichtKapazitaet,
                    Pausenstunden = NeueSchichtPausenstunden,
                    Zuschlagsstunden = NeueSchichtZuschlagsstunden,
                    Start = GetStartForWochentag(NeueSchichtWochentag),
                    Ende = GetStartForWochentag(NeueSchichtWochentag).AddHours(8)
                };
                SchichtListe.Add(neueSchicht);

                NeueSchichtName = string.Empty;
                NeueSchichtAbteilung = string.Empty;
                NeueSchichtWochentag = string.Empty;
                NeueSchichtKapazitaet = 2;
                SetStatus("Schicht hinzugefügt");
            });
        }

        private void Zuweisen(object obj)
        {
            FuehreMitRollenpruefungAus("Dienstplan ändern", () => 
                SetStatus(_service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht, AktuellerBenutzer)));
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

        private void Seed()
        {
            LadeDaten();
        }

        private void LadeDaten()
        {
            var max = new Mitarbeiter
            {
                Id = 1,
                MandantId = 1,
                FilialeId = 1,
                Name = "Max Mustermann",
                Abteilung = "Kasse",
                Qualifikation = "Standard",
                IstAktiv = true
            };
            var erika = new Mitarbeiter
            {
                Id = 2,
                Name = "Erika Beispiel",
                Abteilung = "Lager",
                Qualifikation = "Stapler",
                IstAktiv = true
            };

            var frueh = new Schicht
            {
                Id = 1,
                MandantId = 1,
                FilialeId = 1,
                FilialeName = "Zentrale",
                Name = "Frühschicht",
                Abteilung = "Kasse",
                Rolle = "Kassenleitung",
                Wochentag = "Montag",
                Start = DateTime.Today.AddHours(6),
                Ende = DateTime.Today.AddHours(14),
                BenoetigteMitarbeiter = 2,
                Pausenstunden = 0.5m,
                Zuschlagsstunden = 1.0m,
                BenoetigteQualifikation = "Standard"
            };

            MitarbeiterListe.Add(max);
            MitarbeiterListe.Add(erika);
            SchichtListe.Add(frueh);
            _service.Zuweisen(max, frueh, AktuellerBenutzer);

            ForecastListe.Add(new UmsatzForecast
            {
                FilialeId = 1,
                FilialeName = "Zentrale",
                Datum = DateTime.Today,
                ErwarteterUmsatz = 12500,
                ErwarteteKundenfrequenz = 980
            });

            Verfuegbarkeiten.Add(new Availability
            {
                Id = 1,
                MitarbeiterId = 1,
                MitarbeiterName = "Max Mustermann",
                Wochentag = "Montag",
                Von = new TimeSpan(8, 0, 0),
                Bis = new TimeSpan(16, 0, 0),
                Status = RequestStatus.Approved,
                Kommentar = "Regelverfügbarkeit"
            });

            Abwesenheiten.Add(new LeaveRequest
            {
                Id = 1,
                MitarbeiterId = 2,
                MitarbeiterName = "Erika Beispiel",
                Von = DateTime.Today.AddHours(8),
                Bis = DateTime.Today.AddHours(16),
                Grund = "Urlaub",
                Status = RequestStatus.Submitted,
                Kommentar = "Familientermin"
            });

            SetStatus("Bereit");
        }

        private void SetStatus(string nachricht)
        {
            StatusNachricht = nachricht;
            OnPropertyChanged(nameof(StatusNachricht));
        }

        private static List<int> ParseSkillIds(string skillIds)
        {
            if (string.IsNullOrWhiteSpace(skillIds))
                return new List<int>();

            return skillIds
                .Split(new[] { ',', ';', ' ' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(ParseIntOrZero)
                .Where(id => id > 0)
                .ToList();
        }

        private static int ParseIntOrZero(string value)
        {
            int parsed;
            return int.TryParse(value, out parsed) ? parsed : 0;
        }

        private DateTime GetStartForWochentag(string wochentag)
        {
            var dayOfWeek = ParseWochentag(wochentag);
            var today = DateTime.Today;
            var daysUntilTarget = ((int)dayOfWeek - (int)today.DayOfWeek + 7) % 7;

            return today.AddDays(daysUntilTarget).AddHours(8);
        }

        private DayOfWeek ParseWochentag(string wochentag)
        {
            switch ((wochentag ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "montag":
                    return DayOfWeek.Monday;
                case "dienstag":
                    return DayOfWeek.Tuesday;
                case "mittwoch":
                    return DayOfWeek.Wednesday;
                case "donnerstag":
                    return DayOfWeek.Thursday;
                case "freitag":
                    return DayOfWeek.Friday;
                case "samstag":
                case "sonnabend":
                    return DayOfWeek.Saturday;
                case "sonntag":
                    return DayOfWeek.Sunday;
                default:
                    return DateTime.Today.DayOfWeek;
            }
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void SetInputProperty<T>(ref T field, T value, [CallerMemberName] string propertyName = null)
        {
            if (SetProperty(ref field, value, propertyName))
            {
                if (propertyName == nameof(NeueSchichtStartzeit))
                    OnPropertyChanged(nameof(NeueSchichtEndzeit));

                OnPropertyChanged(nameof(MitarbeiterFehlerNachricht));
                OnPropertyChanged(nameof(SchichtFehlerNachricht));
            }
        }

        private bool SetProperty<T>(ref T field, T value, [CallerMemberName] string propertyName = null)
        {
            if (Equals(field, value))
                return false;

            field = value;
            OnPropertyChanged(propertyName);
            return true;
        }

        private void OnPropertyChanged([CallerMemberName] string n = null)
        {
            var handler = PropertyChanged;
            if (handler != null)
                handler(this, new PropertyChangedEventArgs(n));
        }
    }
}
