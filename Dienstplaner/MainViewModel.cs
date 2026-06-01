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
    public class MainViewModel : INotifyPropertyChanged, IDataErrorInfo
    {
        private readonly ZuweisungsService _service;

        private Mitarbeiter _ausgewaehlterMitarbeiter;
        private Schicht _ausgewaehlteSchicht;
        private string _neuerMitarbeiterName;
        private string _neueMitarbeiterAbteilung;
        private string _neuerMitarbeiterQualifikation;
        private string _neueSchichtName;
        private string _neueSchichtAbteilung;
        private string _neueSchichtWochentag;
        private string _neueSchichtKapazitaet = "2";
        private string _neueSchichtStartzeit = "08:00";
        private string _neueSchichtEndzeit = "16:00";
        private string _statusNachricht;

        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; set; }
        public ObservableCollection<Schicht> SchichtListe { get; set; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

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

        // Inputs
        public string NeuerMitarbeiterName
        {
            get { return _neuerMitarbeiterName; }
            set { SetInputProperty(ref _neuerMitarbeiterName, value); }
        }

        public string NeueMitarbeiterAbteilung
        {
            get { return _neueMitarbeiterAbteilung; }
            set { SetInputProperty(ref _neueMitarbeiterAbteilung, value); }
        }

        public string NeuerMitarbeiterQualifikation
        {
            get { return _neuerMitarbeiterQualifikation; }
            set { SetInputProperty(ref _neuerMitarbeiterQualifikation, value); }
        }

        public string NeueSchichtName
        {
            get { return _neueSchichtName; }
            set { SetInputProperty(ref _neueSchichtName, value); }
        }

        public string NeueSchichtAbteilung
        {
            get { return _neueSchichtAbteilung; }
            set { SetInputProperty(ref _neueSchichtAbteilung, value); }
        }

        public string NeueSchichtWochentag
        {
            get { return _neueSchichtWochentag; }
            set { SetInputProperty(ref _neueSchichtWochentag, value); }
        }

        public string NeueSchichtKapazitaet
        {
            get { return _neueSchichtKapazitaet; }
            set { SetInputProperty(ref _neueSchichtKapazitaet, value); }
        }

        public string NeueSchichtStartzeit
        {
            get { return _neueSchichtStartzeit; }
            set { SetInputProperty(ref _neueSchichtStartzeit, value); }
        }

        public string NeueSchichtEndzeit
        {
            get { return _neueSchichtEndzeit; }
            set { SetInputProperty(ref _neueSchichtEndzeit, value); }
        }

        public string MitarbeiterFehlerNachricht
        {
            get
            {
                string fehler;
                return IstMitarbeiterGueltig(out fehler) ? string.Empty : fehler;
            }
        }

        public string SchichtFehlerNachricht
        {
            get
            {
                string fehler;
                return IstSchichtGueltig(out fehler) ? string.Empty : fehler;
            }
        }

        public string StatusNachricht
        {
            get { return _statusNachricht; }
            set { SetProperty(ref _statusNachricht, value); }
        }

        public string Error
        {
            get { return string.Empty; }
        }

        public string this[string propertyName]
        {
            get { return ValidiereProperty(propertyName); }
        }

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);

            _service = new ZuweisungsService();

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter, CanAddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht, CanAddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);

            Seed();
        }

        private bool CanAddMitarbeiter(object obj)
        {
            string fehler;
            return IstMitarbeiterGueltig(out fehler);
        }

        private bool CanAddSchicht(object obj)
        {
            string fehler;
            return IstSchichtGueltig(out fehler);
        }

        private void AddMitarbeiter(object obj)
        {
            string fehler;
            if (!IstMitarbeiterGueltig(out fehler))
            {
                StatusNachricht = fehler;
                return;
            }

            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = MitarbeiterListe.Count + 1,
                Name = NeuerMitarbeiterName.Trim(),
                Abteilung = NeueMitarbeiterAbteilung.Trim(),
                Qualifikation = NeuerMitarbeiterQualifikation.Trim(),
                IstAktiv = true
            });

            StatusNachricht = "Mitarbeiter hinzugefügt";
        }

        private void AddSchicht(object obj)
        {
            string fehler;
            int kapazitaet;
            TimeSpan startzeit;
            TimeSpan endzeit;

            if (!IstSchichtGueltig(out fehler, out kapazitaet, out startzeit, out endzeit))
            {
                StatusNachricht = fehler;
                return;
            }

            DateTime datum = DateTime.Today;

            SchichtListe.Add(new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName.Trim(),
                Abteilung = NeueSchichtAbteilung.Trim(),
                Wochentag = NeueSchichtWochentag.Trim(),
                Start = datum.Add(startzeit),
                Ende = datum.Add(endzeit),
                BenoetigteMitarbeiter = kapazitaet
            });

            StatusNachricht = "Schicht hinzugefügt";
        }

        private void Zuweisen(object obj)
        {
            StatusNachricht = _service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);
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
            int.TryParse(NeueSchichtKapazitaet, out kapazitaet);
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

        private static string PflichtfeldFehler(string wert, string feldname)
        {
            return string.IsNullOrWhiteSpace(wert) ? feldname + " ist ein Pflichtfeld." : string.Empty;
        }

        private static string ValidiereKapazitaet(string wert)
        {
            int kapazitaet;

            if (string.IsNullOrWhiteSpace(wert))
                return "Kapazität ist ein Pflichtfeld.";

            if (!int.TryParse(wert, out kapazitaet))
                return "Kapazität muss eine ganze Zahl sein.";

            if (kapazitaet < 1)
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
            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = 1,
                Name = "Max Mustermann",
                Abteilung = "Kasse",
                Qualifikation = "Standard"
            });

            SchichtListe.Add(new Schicht
            {
                Id = 1,
                Name = "Frühschicht",
                Abteilung = "Kasse",
                Wochentag = "Montag",
                Start = DateTime.Today.AddHours(8),
                Ende = DateTime.Today.AddHours(16),
                BenoetigteMitarbeiter = 2
            });
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
                CommandManager.InvalidateRequerySuggested();
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
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
