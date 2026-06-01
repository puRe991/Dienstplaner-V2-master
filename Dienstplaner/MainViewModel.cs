using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows.Data;
using System.Windows.Input;
using Dienstplaner.Helpers;
using Dienstplaner.Models;
using Dienstplaner.Services;

namespace Dienstplaner.ViewModels
{
    public class MainViewModel : INotifyPropertyChanged
    {
        private readonly ZuweisungsService _service;
        private readonly ApprovalService _approvalService;
        private string _statusNachricht;

        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; set; }
        public ObservableCollection<Schicht> SchichtListe { get; set; }
        public ObservableCollection<ReportKennzahl> ReportListe { get; set; }
        public ObservableCollection<UmsatzForecast> ForecastListe { get; set; }
        public ObservableCollection<PayrollRecord> LohnabrechnungListe { get; set; }
        public ObservableCollection<TimeTrackingRecord> ZeiterfassungListe { get; set; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

        public Mitarbeiter AusgewaehlterMitarbeiter { get; set; }
        public Schicht AusgewaehlteSchicht { get; set; }
        public Availability AusgewaehlteVerfuegbarkeit { get; set; }
        public Absence AusgewaehlteAbwesenheit { get; set; }
        public ShiftSwapRequest AusgewaehlterTauschAntrag { get; set; }

        public MandantKontext AktuellerKontext { get; set; }

        // Inputs
        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }
        public decimal NeueMitarbeiterSollstunden { get; set; } = 40;
        public decimal NeuerMitarbeiterStundenlohn { get; set; } = 15;

        public string NeueSchichtName { get; set; }
        public string NeueSchichtAbteilung { get; set; }
        public string NeueSchichtWochentag { get; set; }
        public int NeueSchichtKapazitaet { get; set; } = 2;
        public decimal NeueSchichtPausenstunden { get; set; } = 0.5m;
        public decimal NeueSchichtZuschlagsstunden { get; set; }
        public string ForecastImportPfad { get; set; }

        public string StatusNachricht { get; set; }
        public string DsgvoExportText { get; set; }
        public ComplianceRichtlinie ComplianceRichtlinie { get; }
        public BenutzerKontext AktuellerBenutzer { get; }

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }
        public ICommand CsvExportCommand { get; }
        public ICommand ExcelExportCommand { get; }
        public ICommand PdfExportCommand { get; }
        public ICommand ReportsAktualisierenCommand { get; }
        public ICommand IntegrationenAktualisierenCommand { get; }
        public ICommand ForecastImportCommand { get; }

        private readonly ZuweisungsService _service;
        private readonly DienstplanExportService _exportService;
        private readonly ReportingService _reportingService;
        private readonly IntegrationsService _integrationsService;
        private readonly ForecastImportService _forecastImportService;

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();
            ReportListe = new ObservableCollection<ReportKennzahl>();
            ForecastListe = new ObservableCollection<UmsatzForecast>();
            LohnabrechnungListe = new ObservableCollection<PayrollRecord>();
            ZeiterfassungListe = new ObservableCollection<TimeTrackingRecord>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);

            AktuellerKontext = new MandantKontext
            {
                MandantId = 1,
                MandantName = "DemoMandant",
                FilialeId = 1,
                FilialeName = "Zentrale",
                Rolle = BenutzerRolle.Personalwesen
            };

            _service = new ZuweisungsService();
            _exportService = new DienstplanExportService();
            _reportingService = new ReportingService();
            _integrationsService = new IntegrationsService();
            _forecastImportService = new ForecastImportService();

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht);
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

        private void AddMitarbeiter(object obj)
        {
            FuehreMitRollenpruefungAus("Mitarbeiter erstellen", () =>
            {
                Id = MitarbeiterListe.Count + 1,
                MandantId = AktuellerKontext.MandantId,
                FilialeId = AktuellerKontext.FilialeId,
                Name = NeuerMitarbeiterName,
                Abteilung = NeueMitarbeiterAbteilung,
                Qualifikation = NeuerMitarbeiterQualifikation,
                SollstundenProWoche = NeueMitarbeiterSollstunden,
                WochenstundenLimit = 48,
                Stundenlohn = NeuerMitarbeiterStundenlohn,
                IstAktiv = true
            });

            StatusNachricht = "Mitarbeiter hinzugefügt";
            OnPropertyChanged("StatusNachricht");
        }

        private void AddSchicht(object obj)
        {
            FuehreMitRollenpruefungAus("Schicht erstellen", () =>
            {
                Id = SchichtListe.Count + 1,
                MandantId = AktuellerKontext.MandantId,
                FilialeId = AktuellerKontext.FilialeId,
                FilialeName = AktuellerKontext.FilialeName,
                Name = NeueSchichtName,
                Abteilung = NeueSchichtAbteilung,
                Wochentag = NeueSchichtWochentag,
                BenoetigteMitarbeiter = NeueSchichtKapazitaet,
                Pausenstunden = NeueSchichtPausenstunden,
                Zuschlagsstunden = NeueSchichtZuschlagsstunden,
                Start = DateTime.Today.AddHours(8),
                Ende = DateTime.Today.AddHours(16)
            });

            StatusNachricht = "Schicht hinzugefügt";
            OnPropertyChanged("StatusNachricht");
        }

        private void Zuweisen(object obj)
        {
            FuehreMitRollenpruefungAus("Dienstplan ändern", () => SetStatus(_service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht, AktuellerBenutzer)));
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
                var alteWerte = schicht.ToAuditString();
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
                MitarbeiterView.Refresh();
                SchichtView.Refresh();
            }
            catch (UnauthorizedAccessException ex)
            {
                SetStatus(ex.Message);
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

        private void Seed()
        {
            Mitarbeiter max = new Mitarbeiter
            {
                Id = 1,
                MandantId = 1,
                FilialeId = 1,
                Name = "Max Mustermann",
                Abteilung = "Kasse",
                Qualifikation = "Standard",
                IstAktiv = true
            });

            Schicht frueh = new Schicht
            {
                Id = 1,
                MandantId = 1,
                FilialeId = 1,
                FilialeName = "Zentrale",
                Name = "Frühschicht",
                Abteilung = "Kasse",
                Wochentag = "Montag",
                Start = DateTime.Today.AddHours(6),
                Ende = DateTime.Today.AddHours(14),
                BenoetigteMitarbeiter = 2,
                Pausenstunden = 0.5m,
                Zuschlagsstunden = 1.0m,
                BenoetigteQualifikation = "Standard"
            };

            MitarbeiterListe.Add(max);
            SchichtListe.Add(frueh);
            _service.Zuweisen(max, frueh);

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

            StatusNachricht = "Bereit";
        }

        private void SetStatus(string nachricht)
        {
            StatusNachricht = nachricht;
            OnPropertyChanged(nameof(StatusNachricht));
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
