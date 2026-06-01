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
        private readonly ZuweisungsService _service;
        private readonly ApprovalService _approvalService;
        private string _statusNachricht;

        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; set; }
        public ObservableCollection<Schicht> SchichtListe { get; set; }
        public ObservableCollection<Availability> Verfuegbarkeiten { get; set; }
        public ObservableCollection<Absence> Abwesenheiten { get; set; }
        public ObservableCollection<ShiftSwapRequest> TauschAntraege { get; set; }
        public ObservableCollection<DecisionLogEntry> EntscheidungsLog { get; set; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

        public Mitarbeiter AusgewaehlterMitarbeiter { get; set; }
        public Schicht AusgewaehlteSchicht { get; set; }
        public Availability AusgewaehlteVerfuegbarkeit { get; set; }
        public Absence AusgewaehlteAbwesenheit { get; set; }
        public ShiftSwapRequest AusgewaehlterTauschAntrag { get; set; }

        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }

        public string NeueSchichtName { get; set; }
        public string NeueSchichtAbteilung { get; set; }
        public string NeueSchichtWochentag { get; set; }
        public int NeueSchichtKapazitaet { get; set; } = 2;

        public string VerfuegbarkeitWochentag { get; set; }
        public string VerfuegbarkeitVon { get; set; } = "08:00";
        public string VerfuegbarkeitBis { get; set; } = "16:00";
        public string AntragKommentar { get; set; }
        public string AbwesenheitVon { get; set; }
        public string AbwesenheitBis { get; set; }
        public string AbwesenheitGrund { get; set; }
        public string EntscheidungsBenutzer { get; set; } = "Filialleitung";
        public string EntscheidungsKommentar { get; set; }
        public ApprovalRole EntscheidungsRolle { get; set; } = ApprovalRole.Filialleiter;

        public Array StatusWerte
        {
            get { return Enum.GetValues(typeof(RequestStatus)); }
        }

        public Array Rollen
        {
            get { return Enum.GetValues(typeof(ApprovalRole)); }
        }

        public string StatusNachricht
        {
            get { return _statusNachricht; }
            set
            {
                _statusNachricht = value;
                OnPropertyChanged();
            }
        }

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }
        public ICommand VerfuegbarkeitEinreichenCommand { get; }
        public ICommand UrlaubsantragEinreichenCommand { get; }
        public ICommand KrankmeldungEinreichenCommand { get; }
        public ICommand TauschAntragEinreichenCommand { get; }
        public ICommand VerfuegbarkeitGenehmigenCommand { get; }
        public ICommand VerfuegbarkeitAblehnenCommand { get; }
        public ICommand AbwesenheitGenehmigenCommand { get; }
        public ICommand AbwesenheitAblehnenCommand { get; }
        public ICommand TauschGenehmigenCommand { get; }
        public ICommand TauschAblehnenCommand { get; }

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();
            Verfuegbarkeiten = new ObservableCollection<Availability>();
            Abwesenheiten = new ObservableCollection<Absence>();
            TauschAntraege = new ObservableCollection<ShiftSwapRequest>();
            EntscheidungsLog = new ObservableCollection<DecisionLogEntry>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);

            _service = new ZuweisungsService();
            _approvalService = new ApprovalService();

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);
            VerfuegbarkeitEinreichenCommand = new RelayCommand(VerfuegbarkeitEinreichen);
            UrlaubsantragEinreichenCommand = new RelayCommand(UrlaubsantragEinreichen);
            KrankmeldungEinreichenCommand = new RelayCommand(KrankmeldungEinreichen);
            TauschAntragEinreichenCommand = new RelayCommand(TauschAntragEinreichen);
            VerfuegbarkeitGenehmigenCommand = new RelayCommand(obj => Entscheide(AusgewaehlteVerfuegbarkeit, RequestStatus.Approved));
            VerfuegbarkeitAblehnenCommand = new RelayCommand(obj => Entscheide(AusgewaehlteVerfuegbarkeit, RequestStatus.Rejected));
            AbwesenheitGenehmigenCommand = new RelayCommand(obj => Entscheide(AusgewaehlteAbwesenheit, RequestStatus.Approved));
            AbwesenheitAblehnenCommand = new RelayCommand(obj => Entscheide(AusgewaehlteAbwesenheit, RequestStatus.Rejected));
            TauschGenehmigenCommand = new RelayCommand(obj => Entscheide(AusgewaehlterTauschAntrag, RequestStatus.Approved));
            TauschAblehnenCommand = new RelayCommand(obj => Entscheide(AusgewaehlterTauschAntrag, RequestStatus.Rejected));

            Seed();
        }

        private void AddMitarbeiter(object obj)
        {
            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = MitarbeiterListe.Count + 1,
                Name = NeuerMitarbeiterName,
                Abteilung = NeueMitarbeiterAbteilung,
                Qualifikation = NeuerMitarbeiterQualifikation,
                IstAktiv = true
            });

            StatusNachricht = "Mitarbeiter hinzugefügt";
        }

        private void AddSchicht(object obj)
        {
            var start = DateTime.Today.AddHours(8).AddDays(SchichtListe.Count);
            SchichtListe.Add(new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName,
                Abteilung = NeueSchichtAbteilung,
                Wochentag = NeueSchichtWochentag,
                Start = start,
                Ende = start.AddHours(8),
                BenoetigteMitarbeiter = NeueSchichtKapazitaet
            });

            StatusNachricht = "Schicht hinzugefügt";
        }

        private void Zuweisen(object obj)
        {
            StatusNachricht = _service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht, Verfuegbarkeiten, Abwesenheiten);
        }

        private void VerfuegbarkeitEinreichen(object obj)
        {
            if (AusgewaehlterMitarbeiter == null)
            {
                StatusNachricht = "Bitte Mitarbeiter auswählen";
                return;
            }

            TimeSpan von;
            TimeSpan bis;
            if (!TimeSpan.TryParse(VerfuegbarkeitVon, out von) || !TimeSpan.TryParse(VerfuegbarkeitBis, out bis))
            {
                StatusNachricht = "Verfügbarkeitszeiten sind ungültig";
                return;
            }

            Verfuegbarkeiten.Add(new Availability
            {
                Id = Verfuegbarkeiten.Count + 1,
                MitarbeiterId = AusgewaehlterMitarbeiter.Id,
                MitarbeiterName = AusgewaehlterMitarbeiter.Name,
                Wochentag = VerfuegbarkeitWochentag,
                Von = von,
                Bis = bis,
                Kommentar = AntragKommentar,
                Status = RequestStatus.Submitted
            });

            StatusNachricht = "Verfügbarkeit eingereicht";
        }

        private void UrlaubsantragEinreichen(object obj)
        {
            AbsenceEinreichen(new LeaveRequest { IstBezahlt = true }, "Urlaubsantrag eingereicht");
        }

        private void KrankmeldungEinreichen(object obj)
        {
            AbsenceEinreichen(new SickLeave { ArbeitsunfaehigkeitsBescheinigungVorhanden = true }, "Krankmeldung eingereicht");
        }

        private void AbsenceEinreichen(Absence absence, string erfolgsmeldung)
        {
            if (AusgewaehlterMitarbeiter == null)
            {
                StatusNachricht = "Bitte Mitarbeiter auswählen";
                return;
            }

            DateTime von;
            DateTime bis;
            if (!DateTime.TryParse(AbwesenheitVon, out von) || !DateTime.TryParse(AbwesenheitBis, out bis))
            {
                StatusNachricht = "Abwesenheitszeitraum ist ungültig";
                return;
            }

            absence.Id = Abwesenheiten.Count + 1;
            absence.MitarbeiterId = AusgewaehlterMitarbeiter.Id;
            absence.MitarbeiterName = AusgewaehlterMitarbeiter.Name;
            absence.Von = von;
            absence.Bis = bis;
            absence.Grund = AbwesenheitGrund;
            absence.Kommentar = AntragKommentar;
            absence.Status = RequestStatus.Submitted;
            Abwesenheiten.Add(absence);

            StatusNachricht = erfolgsmeldung;
        }

        private void TauschAntragEinreichen(object obj)
        {
            if (AusgewaehlterMitarbeiter == null || AusgewaehlteSchicht == null)
            {
                StatusNachricht = "Bitte Mitarbeiter und Schicht auswählen";
                return;
            }

            TauschAntraege.Add(new ShiftSwapRequest
            {
                Id = TauschAntraege.Count + 1,
                MitarbeiterId = AusgewaehlterMitarbeiter.Id,
                MitarbeiterName = AusgewaehlterMitarbeiter.Name,
                VonMitarbeiterId = AusgewaehlterMitarbeiter.Id,
                VonMitarbeiterName = AusgewaehlterMitarbeiter.Name,
                SchichtId = AusgewaehlteSchicht.Id,
                SchichtName = AusgewaehlteSchicht.Name,
                Kommentar = AntragKommentar,
                Status = RequestStatus.Submitted
            });

            StatusNachricht = "Schichttausch eingereicht";
        }

        private void Entscheide(EmployeeRequest request, RequestStatus status)
        {
            var log = _approvalService.Entscheiden(request, status, EntscheidungsBenutzer, EntscheidungsRolle, EntscheidungsKommentar);
            if (log == null)
            {
                StatusNachricht = "Entscheidung nicht erlaubt";
                return;
            }

            EntscheidungsLog.Add(log);
            StatusNachricht = string.Format("{0} wurde {1}", log.AntragTyp, status);
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

            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = 2,
                Name = "Erika Beispiel",
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
                Start = DateTime.Today.AddHours(8),
                Ende = DateTime.Today.AddHours(16),
                BenoetigteMitarbeiter = 2,
                BenoetigteQualifikation = "Standard"
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

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
