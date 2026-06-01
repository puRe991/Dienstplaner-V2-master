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

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }

        private readonly ZuweisungsService _service;

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();

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
            if (!ValidateMitarbeiter())
                return;

            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = MitarbeiterListe.Count + 1,
                Name = NeuerMitarbeiterName.Trim(),
                Abteilung = NeueMitarbeiterAbteilung.Trim(),
                Qualifikation = NeuerMitarbeiterQualifikation.Trim(),
                IstAktiv = true
            });

            SetStatus("Mitarbeiter hinzugefügt");
        }

        private void AddSchicht(object obj)
        {
            if (!ValidateSchicht())
                return;

            SchichtListe.Add(new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName.Trim(),
                Abteilung = NeueSchichtAbteilung.Trim(),
                Wochentag = NeueSchichtWochentag.Trim(),
                BenoetigteMitarbeiter = NeueSchichtKapazitaet
            });

            SetStatus("Schicht hinzugefügt");
        }

        private bool ValidateMitarbeiter()
        {
            if (string.IsNullOrWhiteSpace(NeuerMitarbeiterName))
            {
                SetStatus("Mitarbeitername ist erforderlich");
                return false;
            }

            if (string.IsNullOrWhiteSpace(NeueMitarbeiterAbteilung))
            {
                SetStatus("Mitarbeiterabteilung ist erforderlich");
                return false;
            }

            if (string.IsNullOrWhiteSpace(NeuerMitarbeiterQualifikation))
            {
                SetStatus("Mitarbeiterqualifikation ist erforderlich");
                return false;
            }

            return true;
        }

        private bool ValidateSchicht()
        {
            if (string.IsNullOrWhiteSpace(NeueSchichtName))
            {
                SetStatus("Schichtname ist erforderlich");
                return false;
            }

            if (string.IsNullOrWhiteSpace(NeueSchichtAbteilung))
            {
                SetStatus("Schichtabteilung ist erforderlich");
                return false;
            }

            if (string.IsNullOrWhiteSpace(NeueSchichtWochentag))
            {
                SetStatus("Schichtwochentag ist erforderlich");
                return false;
            }

            if (NeueSchichtKapazitaet <= 0)
            {
                SetStatus("Schichtkapazität muss größer als 0 sein");
                return false;
            }

            return true;
        }

        private void Zuweisen(object obj)
        {
            SetStatus(_service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht));
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

        private void SetStatus(string message)
        {
            StatusNachricht = message;
            OnPropertyChanged(nameof(StatusNachricht));
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
