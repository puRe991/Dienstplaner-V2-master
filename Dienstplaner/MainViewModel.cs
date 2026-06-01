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
        private Mitarbeiter _ausgewaehlterMitarbeiter;
        private Schicht _ausgewaehlteSchicht;
        private string _neuerMitarbeiterName;
        private string _neueMitarbeiterAbteilung;
        private string _neuerMitarbeiterQualifikation;
        private string _neueSchichtName;
        private string _neueSchichtAbteilung;
        private string _neueSchichtWochentag;
        private int _neueSchichtKapazitaet = 2;
        private string _statusNachricht;

        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; }
        public ObservableCollection<Schicht> SchichtListe { get; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

        public Mitarbeiter AusgewaehlterMitarbeiter
        {
            get { return _ausgewaehlterMitarbeiter; }
            set
            {
                if (_ausgewaehlterMitarbeiter == value)
                    return;

                _ausgewaehlterMitarbeiter = value;
                OnPropertyChanged();
                ZuweisenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public Schicht AusgewaehlteSchicht
        {
            get { return _ausgewaehlteSchicht; }
            set
            {
                if (_ausgewaehlteSchicht == value)
                    return;

                _ausgewaehlteSchicht = value;
                OnPropertyChanged();
                ZuweisenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        // Inputs
        public string NeuerMitarbeiterName
        {
            get { return _neuerMitarbeiterName; }
            set
            {
                if (_neuerMitarbeiterName == value)
                    return;

                _neuerMitarbeiterName = value;
                OnPropertyChanged();
                MitarbeiterHinzufuegenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public string NeueMitarbeiterAbteilung
        {
            get { return _neueMitarbeiterAbteilung; }
            set
            {
                if (_neueMitarbeiterAbteilung == value)
                    return;

                _neueMitarbeiterAbteilung = value;
                OnPropertyChanged();
                MitarbeiterHinzufuegenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public string NeuerMitarbeiterQualifikation
        {
            get { return _neuerMitarbeiterQualifikation; }
            set
            {
                if (_neuerMitarbeiterQualifikation == value)
                    return;

                _neuerMitarbeiterQualifikation = value;
                OnPropertyChanged();
                MitarbeiterHinzufuegenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public string NeueSchichtName
        {
            get { return _neueSchichtName; }
            set
            {
                if (_neueSchichtName == value)
                    return;

                _neueSchichtName = value;
                OnPropertyChanged();
                SchichtHinzufuegenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public string NeueSchichtAbteilung
        {
            get { return _neueSchichtAbteilung; }
            set
            {
                if (_neueSchichtAbteilung == value)
                    return;

                _neueSchichtAbteilung = value;
                OnPropertyChanged();
                SchichtHinzufuegenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public string NeueSchichtWochentag
        {
            get { return _neueSchichtWochentag; }
            set
            {
                if (_neueSchichtWochentag == value)
                    return;

                _neueSchichtWochentag = value;
                OnPropertyChanged();
                SchichtHinzufuegenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public int NeueSchichtKapazitaet
        {
            get { return _neueSchichtKapazitaet; }
            set
            {
                if (_neueSchichtKapazitaet == value)
                    return;

                _neueSchichtKapazitaet = value;
                OnPropertyChanged();
                SchichtHinzufuegenRelayCommand.RaiseCanExecuteChanged();
            }
        }

        public string StatusNachricht
        {
            get { return _statusNachricht; }
            set
            {
                if (_statusNachricht == value)
                    return;

                _statusNachricht = value;
                OnPropertyChanged();
            }
        }

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }

        private RelayCommand MitarbeiterHinzufuegenRelayCommand { get; }
        private RelayCommand SchichtHinzufuegenRelayCommand { get; }
        private RelayCommand ZuweisenRelayCommand { get; }

        private readonly ZuweisungsService _service;

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);

            _service = new ZuweisungsService();

            MitarbeiterHinzufuegenRelayCommand = new RelayCommand(AddMitarbeiter, CanAddMitarbeiter);
            SchichtHinzufuegenRelayCommand = new RelayCommand(AddSchicht, CanAddSchicht);
            ZuweisenRelayCommand = new RelayCommand(Zuweisen, CanZuweisen);

            MitarbeiterHinzufuegenCommand = MitarbeiterHinzufuegenRelayCommand;
            SchichtHinzufuegenCommand = SchichtHinzufuegenRelayCommand;
            ZuweisenCommand = ZuweisenRelayCommand;

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

            NeuerMitarbeiterName = string.Empty;
            NeueMitarbeiterAbteilung = string.Empty;
            NeuerMitarbeiterQualifikation = string.Empty;
            StatusNachricht = "Mitarbeiter hinzugefügt";
        }

        private bool CanAddMitarbeiter(object obj)
        {
            return !string.IsNullOrWhiteSpace(NeuerMitarbeiterName)
                && !string.IsNullOrWhiteSpace(NeueMitarbeiterAbteilung)
                && !string.IsNullOrWhiteSpace(NeuerMitarbeiterQualifikation);
        }

        private void AddSchicht(object obj)
        {
            SchichtListe.Add(new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName,
                Abteilung = NeueSchichtAbteilung,
                Wochentag = NeueSchichtWochentag,
                BenoetigteMitarbeiter = NeueSchichtKapazitaet
            });

            NeueSchichtName = string.Empty;
            NeueSchichtAbteilung = string.Empty;
            NeueSchichtWochentag = string.Empty;
            NeueSchichtKapazitaet = 2;
            StatusNachricht = "Schicht hinzugefügt";
        }

        private bool CanAddSchicht(object obj)
        {
            return !string.IsNullOrWhiteSpace(NeueSchichtName)
                && !string.IsNullOrWhiteSpace(NeueSchichtAbteilung)
                && !string.IsNullOrWhiteSpace(NeueSchichtWochentag)
                && NeueSchichtKapazitaet > 0;
        }

        private void Zuweisen(object obj)
        {
            StatusNachricht = _service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);
        }

        private bool CanZuweisen(object obj)
        {
            return AusgewaehlterMitarbeiter != null && AusgewaehlteSchicht != null;
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
                BenoetigteMitarbeiter = 2
            });
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
