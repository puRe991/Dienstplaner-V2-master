using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Data;
using System.Windows.Input;
using Dienstplaner.Auth;
using Dienstplaner.Helpers;
using Dienstplaner.Models;
using Dienstplaner.Services;

namespace Dienstplaner.ViewModels
{
    public class MainViewModel : INotifyPropertyChanged
    {
        private readonly ZuweisungsService _service;
        private readonly AuthService _authService;
        private readonly AuthorizationService _authorizationService;

        private Mitarbeiter _ausgewaehlterMitarbeiter;
        private Schicht _ausgewaehlteSchicht;
        private UserAccount _ausgewaehltesBenutzerkonto;
        private AuthenticatedUser _aktuellerBenutzer;
        private string _neuerMitarbeiterName;
        private string _neueMitarbeiterAbteilung;
        private string _neuerMitarbeiterQualifikation;
        private string _neueSchichtName;
        private string _neueSchichtAbteilung;
        private string _neueSchichtWochentag;
        private int _neueSchichtKapazitaet = 2;
        private string _statusNachricht;

        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; private set; }
        public ObservableCollection<Schicht> SchichtListe { get; private set; }
        public ObservableCollection<MitarbeiterAnfrage> AnfrageListe { get; private set; }
        public ObservableCollection<UserAccount> Benutzerkonten { get; private set; }

        public ICollectionView MitarbeiterView { get; private set; }
        public ICollectionView SchichtView { get; private set; }
        public ICollectionView AnfrageView { get; private set; }

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();
            AnfrageListe = new ObservableCollection<MitarbeiterAnfrage>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);
            AnfrageView = CollectionViewSource.GetDefaultView(AnfrageListe);
            MitarbeiterView.Filter = CanCurrentUserViewEmployee;
            SchichtView.Filter = CanCurrentUserViewShift;
            AnfrageView.Filter = CanCurrentUserViewRequest;

            _service = new ZuweisungsService();
            _authorizationService = new AuthorizationService();
            _authService = new AuthService(_authorizationService);
            Benutzerkonten = _authService.DemoAccounts;

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter, _ => KannMitarbeiterBearbeiten);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht, _ => KannDienstplanBearbeiten);
            ZuweisenCommand = new RelayCommand(Zuweisen, _ => KannDienstplanBearbeiten);
            DienstplanFreigebenCommand = new RelayCommand(Freigeben, _ => KannFreigeben);
            ExportCommand = new RelayCommand(Exportieren, _ => KannExportieren);
            AdminCommand = new RelayCommand(AdminOeffnen, _ => KannAdminFunktionenNutzen);

            Seed();
            AusgewaehltesBenutzerkonto = Benutzerkonten[0];
        }

        public Mitarbeiter AusgewaehlterMitarbeiter
        {
            get { return _ausgewaehlterMitarbeiter; }
            set { SetProperty(ref _ausgewaehlterMitarbeiter, value); }
        }

        public Schicht AusgewaehlteSchicht
        {
            get { return _ausgewaehlteSchicht; }
            set { SetProperty(ref _ausgewaehlteSchicht, value); }
        }

        public UserAccount AusgewaehltesBenutzerkonto
        {
            get { return _ausgewaehltesBenutzerkonto; }
            set
            {
                if (SetProperty(ref _ausgewaehltesBenutzerkonto, value))
                    SignIn(value);
            }
        }

        public AuthenticatedUser AktuellerBenutzer
        {
            get { return _aktuellerBenutzer; }
            private set { SetProperty(ref _aktuellerBenutzer, value); }
        }

        public string NeuerMitarbeiterName
        {
            get { return _neuerMitarbeiterName; }
            set { SetProperty(ref _neuerMitarbeiterName, value); }
        }

        public string NeueMitarbeiterAbteilung
        {
            get { return _neueMitarbeiterAbteilung; }
            set { SetProperty(ref _neueMitarbeiterAbteilung, value); }
        }

        public string NeuerMitarbeiterQualifikation
        {
            get { return _neuerMitarbeiterQualifikation; }
            set { SetProperty(ref _neuerMitarbeiterQualifikation, value); }
        }

        public string NeueSchichtName
        {
            get { return _neueSchichtName; }
            set { SetProperty(ref _neueSchichtName, value); }
        }

        public string NeueSchichtAbteilung
        {
            get { return _neueSchichtAbteilung; }
            set { SetProperty(ref _neueSchichtAbteilung, value); }
        }

        public string NeueSchichtWochentag
        {
            get { return _neueSchichtWochentag; }
            set { SetProperty(ref _neueSchichtWochentag, value); }
        }

        public int NeueSchichtKapazitaet
        {
            get { return _neueSchichtKapazitaet; }
            set { SetProperty(ref _neueSchichtKapazitaet, value); }
        }

        public string StatusNachricht
        {
            get { return _statusNachricht; }
            set { SetProperty(ref _statusNachricht, value); }
        }

        public string AktuellerBenutzerText
        {
            get
            {
                return AktuellerBenutzer == null
                    ? "Nicht angemeldet"
                    : string.Format("Angemeldet: {0} · Rolle: {1}", AktuellerBenutzer.DisplayName, AktuellerBenutzer.Role);
            }
        }

        public bool KannMitarbeiterBearbeiten
        {
            get { return _authorizationService.CanEditEmployeeData(AktuellerBenutzer); }
        }

        public bool KannDienstplanBearbeiten
        {
            get { return _authorizationService.CanEditSchedule(AktuellerBenutzer); }
        }

        public bool KannFreigeben
        {
            get { return _authorizationService.HasPermission(AktuellerBenutzer, Permission.ApproveSchedule); }
        }

        public bool KannExportieren
        {
            get { return _authorizationService.HasPermission(AktuellerBenutzer, Permission.ExportSchedule); }
        }

        public bool KannAdminFunktionenNutzen
        {
            get { return _authorizationService.HasPermission(AktuellerBenutzer, Permission.ManageAdminFunctions); }
        }

        public bool IstEmployee
        {
            get { return AktuellerBenutzer != null && AktuellerBenutzer.Role == UserRole.Employee; }
        }

        public ICommand MitarbeiterHinzufuegenCommand { get; private set; }
        public ICommand SchichtHinzufuegenCommand { get; private set; }
        public ICommand ZuweisenCommand { get; private set; }
        public ICommand DienstplanFreigebenCommand { get; private set; }
        public ICommand ExportCommand { get; private set; }
        public ICommand AdminCommand { get; private set; }

        private void SignIn(UserAccount account)
        {
            AktuellerBenutzer = _authService.SignIn(account);
            StatusNachricht = AktuellerBenutzer == null
                ? "Anmeldung fehlgeschlagen"
                : string.Format("{0} ist angemeldet. Rechte wurden angewendet.", AktuellerBenutzer.DisplayName);

            RefreshSecurityState();
        }

        private void AddMitarbeiter(object obj)
        {
            if (!KannMitarbeiterBearbeiten)
            {
                StatusNachricht = "Keine Berechtigung zum Bearbeiten von Mitarbeiterdaten.";
                return;
            }

            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = MitarbeiterListe.Count + 1,
                Name = NeuerMitarbeiterName,
                Abteilung = NeueMitarbeiterAbteilung,
                Qualifikation = NeuerMitarbeiterQualifikation,
                IstAktiv = true
            });

            StatusNachricht = "Mitarbeiter hinzugefügt";
            MitarbeiterView.Refresh();
        }

        private void AddSchicht(object obj)
        {
            if (!KannDienstplanBearbeiten)
            {
                StatusNachricht = "Keine Berechtigung zum Bearbeiten des Dienstplans.";
                return;
            }

            SchichtListe.Add(new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName,
                Abteilung = NeueSchichtAbteilung,
                Wochentag = NeueSchichtWochentag,
                Start = DateTime.Today.AddHours(9),
                Ende = DateTime.Today.AddHours(17),
                BenoetigteMitarbeiter = NeueSchichtKapazitaet
            });

            StatusNachricht = "Schicht hinzugefügt";
            SchichtView.Refresh();
        }

        private void Zuweisen(object obj)
        {
            if (!KannDienstplanBearbeiten)
            {
                StatusNachricht = "Keine Berechtigung zum Zuweisen von Schichten.";
                return;
            }

            StatusNachricht = _service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);
            SchichtView.Refresh();
            MitarbeiterView.Refresh();
        }

        private void Freigeben(object obj)
        {
            StatusNachricht = KannFreigeben
                ? "Dienstplan wurde freigegeben."
                : "Keine Berechtigung für Freigaben.";
        }

        private void Exportieren(object obj)
        {
            StatusNachricht = KannExportieren
                ? "Export wurde für die sichtbaren Daten vorbereitet."
                : "Keine Berechtigung für Exporte.";
        }

        private void AdminOeffnen(object obj)
        {
            StatusNachricht = KannAdminFunktionenNutzen
                ? "Admin-Funktionen sind verfügbar."
                : "Keine Berechtigung für Admin-Funktionen.";
        }

        private bool CanCurrentUserViewEmployee(object item)
        {
            return _authorizationService.CanViewEmployee(AktuellerBenutzer, item as Mitarbeiter);
        }

        private bool CanCurrentUserViewShift(object item)
        {
            return _authorizationService.CanViewShift(AktuellerBenutzer, item as Schicht);
        }

        private bool CanCurrentUserViewRequest(object item)
        {
            return _authorizationService.CanViewRequest(AktuellerBenutzer, item as MitarbeiterAnfrage);
        }

        private void RefreshSecurityState()
        {
            MitarbeiterView.Refresh();
            SchichtView.Refresh();
            AnfrageView.Refresh();
            OnPropertyChanged(nameof(AktuellerBenutzerText));
            OnPropertyChanged(nameof(KannMitarbeiterBearbeiten));
            OnPropertyChanged(nameof(KannDienstplanBearbeiten));
            OnPropertyChanged(nameof(KannFreigeben));
            OnPropertyChanged(nameof(KannExportieren));
            OnPropertyChanged(nameof(KannAdminFunktionenNutzen));
            OnPropertyChanged(nameof(IstEmployee));
            CommandManager.InvalidateRequerySuggested();
        }

        private void Seed()
        {
            var max = new Mitarbeiter
            {
                Id = 1,
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

            var fruehschicht = new Schicht
            {
                Id = 1,
                Name = "Frühschicht",
                Abteilung = "Kasse",
                Wochentag = "Montag",
                Start = DateTime.Today.AddHours(6),
                Ende = DateTime.Today.AddHours(14),
                BenoetigteMitarbeiter = 2
            };
            var spaetschicht = new Schicht
            {
                Id = 2,
                Name = "Spätschicht",
                Abteilung = "Lager",
                Wochentag = "Dienstag",
                Start = DateTime.Today.AddHours(14),
                Ende = DateTime.Today.AddHours(22),
                BenoetigteMitarbeiter = 1
            };

            MitarbeiterListe.Add(max);
            MitarbeiterListe.Add(erika);
            SchichtListe.Add(fruehschicht);
            SchichtListe.Add(spaetschicht);

            _service.Zuweisen(max, fruehschicht);
            _service.Zuweisen(erika, spaetschicht);

            AnfrageListe.Add(new MitarbeiterAnfrage { Id = 1, MitarbeiterId = 1, Titel = "Urlaub am Freitag", Status = "Offen" });
            AnfrageListe.Add(new MitarbeiterAnfrage { Id = 2, MitarbeiterId = 2, Titel = "Schichttausch Dienstag", Status = "In Prüfung" });
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private bool SetProperty<T>(ref T storage, T value, [CallerMemberName] string propertyName = null)
        {
            if (Equals(storage, value))
                return false;

            storage = value;
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
