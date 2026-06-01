using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
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
        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; set; }
        public ObservableCollection<Schicht> SchichtListe { get; set; }
        public ObservableCollection<AuditLogEintrag> AuditLog { get; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

        public Mitarbeiter AusgewaehlterMitarbeiter { get; set; }
        public Schicht AusgewaehlteSchicht { get; set; }

        // Inputs
        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }

        public string NeueSchichtName { get; set; }
        public string NeueSchichtAbteilung { get; set; }
        public string NeueSchichtWochentag { get; set; }
        public int NeueSchichtKapazitaet { get; set; } = 2;

        public string StatusNachricht { get; set; }
        public string DsgvoExportText { get; set; }
        public ComplianceRichtlinie ComplianceRichtlinie { get; }
        public BenutzerKontext AktuellerBenutzer { get; }

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }
        public ICommand SchichtLoeschenCommand { get; }
        public ICommand DienstplanVeroeffentlichenCommand { get; }
        public ICommand DsgvoAuskunftCommand { get; }
        public ICommand DsgvoLoeschenCommand { get; }

        private readonly ZuweisungsService _service;
        private readonly AuditService _auditService;
        private readonly RollenService _rollenService;
        private readonly DsgvoService _dsgvoService;

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);

            var dataProtectionService = new DataProtectionService();
            _rollenService = new RollenService();
            _auditService = new AuditService(dataProtectionService);
            _service = new ZuweisungsService(_auditService, _rollenService);
            _dsgvoService = new DsgvoService(_rollenService, _auditService);

            AuditLog = _auditService.Eintraege;
            ComplianceRichtlinie = new ComplianceRichtlinie();
            AktuellerBenutzer = BenutzerKontext.StandardAdmin();

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);
            SchichtLoeschenCommand = new RelayCommand(SchichtLoeschen);
            DienstplanVeroeffentlichenCommand = new RelayCommand(DienstplanVeroeffentlichen);
            DsgvoAuskunftCommand = new RelayCommand(DsgvoAuskunftErstellen);
            DsgvoLoeschenCommand = new RelayCommand(DsgvoLoeschanfrageBearbeiten);

            Seed();
        }

        private void AddMitarbeiter(object obj)
        {
            FuehreMitRollenpruefungAus("Mitarbeiter erstellen", () =>
            {
                var mitarbeiter = new Mitarbeiter
                {
                    Id = MitarbeiterListe.Count + 1,
                    Name = NeuerMitarbeiterName,
                    Abteilung = NeueMitarbeiterAbteilung,
                    Qualifikation = NeuerMitarbeiterQualifikation,
                    IstAktiv = true
                };

                MitarbeiterListe.Add(mitarbeiter);
                _auditService.Protokolliere(AuditAction.DienstplanErstellt, "Mitarbeiter", mitarbeiter.Id, AktuellerBenutzer, string.Empty, mitarbeiter.ToAuditString(), "Mitarbeiter für Dienstplanung angelegt");
                SetStatus("Mitarbeiter hinzugefügt");
            });
        }

        private void AddSchicht(object obj)
        {
            FuehreMitRollenpruefungAus("Schicht erstellen", () =>
            {
                var schicht = new Schicht
                {
                    Id = SchichtListe.Count + 1,
                    Name = NeueSchichtName,
                    Abteilung = NeueSchichtAbteilung,
                    Wochentag = NeueSchichtWochentag,
                    BenoetigteMitarbeiter = NeueSchichtKapazitaet
                };

                SchichtListe.Add(schicht);
                _auditService.Protokolliere(AuditAction.DienstplanErstellt, "Schicht", schicht.Id, AktuellerBenutzer, string.Empty, schicht.ToAuditString(), "Dienstplan-Schicht erstellt");
                SetStatus("Schicht hinzugefügt");
            });
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
            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = 1,
                Name = "Max Mustermann",
                Abteilung = "Kasse",
                Qualifikation = "Standard",
                IstAktiv = true
            });

            SchichtListe.Add(new Schicht
            {
                Id = 1,
                Name = "Frühschicht",
                Abteilung = "Kasse",
                Wochentag = "Montag",
                BenoetigteMitarbeiter = 2
            });
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
