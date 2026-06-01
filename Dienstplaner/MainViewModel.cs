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
        private string _statusNachricht;

        public ObservableCollection<Mitarbeiter> MitarbeiterListe { get; set; }
        public ObservableCollection<Schicht> SchichtListe { get; set; }
        public ObservableCollection<string> ZuweisungsFehler { get; private set; }
        public ObservableCollection<string> ZuweisungsWarnungen { get; private set; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

        public Mitarbeiter AusgewaehlterMitarbeiter { get; set; }
        public Schicht AusgewaehlteSchicht { get; set; }

        // Inputs
        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }
        public string NeueMitarbeiterFiliale { get; set; }
        public int NeuesMitarbeiterWochenstundenLimit { get; set; } = 40;

        public string NeueSchichtName { get; set; }
        public string NeueSchichtAbteilung { get; set; }
        public string NeueSchichtFiliale { get; set; }
        public string NeueSchichtWochentag { get; set; }
        public string NeueSchichtQualifikation { get; set; }
        public int NeueSchichtKapazitaet { get; set; } = 2;
        public int NeueSchichtPauseInMinuten { get; set; } = 30;

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

        private readonly ZuweisungsService _service;

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();
            ZuweisungsFehler = new ObservableCollection<string>();
            ZuweisungsWarnungen = new ObservableCollection<string>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);

            _service = new ZuweisungsService();

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);

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
                Filiale = NeueMitarbeiterFiliale,
                WochenstundenLimit = NeuesMitarbeiterWochenstundenLimit,
                AktuelleWochenstunden = 0,
                IstAktiv = true
            });

            StatusNachricht = "Mitarbeiter hinzugefügt";
        }

        private void AddSchicht(object obj)
        {
            var start = GetStartForWochentag(NeueSchichtWochentag);

            SchichtListe.Add(new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName,
                Abteilung = NeueSchichtAbteilung,
                Filiale = NeueSchichtFiliale,
                Wochentag = NeueSchichtWochentag,
                Start = start,
                Ende = start.AddHours(8),
                BenoetigteMitarbeiter = NeueSchichtKapazitaet,
                BenoetigteQualifikation = NeueSchichtQualifikation,
                PauseInMinuten = NeueSchichtPauseInMinuten
            });

            StatusNachricht = "Schicht hinzugefügt";
        }

        private void Zuweisen(object obj)
        {
            ZuweisungsFehler.Clear();
            ZuweisungsWarnungen.Clear();

            var result = _service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);

            foreach (var error in result.Errors)
                ZuweisungsFehler.Add(error);

            foreach (var warning in result.Warnings)
                ZuweisungsWarnungen.Add(warning);

            if (result.HasErrors)
                StatusNachricht = string.Format("Zuweisung abgelehnt ({0} Fehler, {1} Warnungen)", result.Errors.Count, result.Warnings.Count);
            else if (result.HasWarnings)
                StatusNachricht = string.Format("Zuweisung erfolgreich mit {0} Warnungen", result.Warnings.Count);
            else
                StatusNachricht = "Zuweisung erfolgreich";
        }

        private void Seed()
        {
            var montag = GetStartForWochentag("Montag");

            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = 1,
                Name = "Max Mustermann",
                Abteilung = "Kasse",
                Filiale = "Berlin-Mitte",
                Qualifikation = "Standard",
                WochenstundenLimit = 40,
                AktuelleWochenstunden = 0,
                IstAktiv = true,
                Verfuegbarkeiten =
                {
                    new Verfuegbarkeit
                    {
                        Von = montag.Date.AddHours(6),
                        Bis = montag.Date.AddHours(18),
                        Hinweis = "Regulär verfügbar"
                    }
                }
            });

            SchichtListe.Add(new Schicht
            {
                Id = 1,
                Name = "Frühschicht",
                Abteilung = "Kasse",
                Filiale = "Berlin-Mitte",
                Wochentag = "Montag",
                Start = montag,
                Ende = montag.AddHours(8),
                BenoetigteMitarbeiter = 2,
                BenoetigteQualifikation = "Standard",
                PauseInMinuten = 30
            });
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

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
