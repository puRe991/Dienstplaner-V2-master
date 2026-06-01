using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Data;
using System.Windows.Input;
using Dienstplaner.Helpers;
using Dienstplaner.Infrastructure.Services;
using Dienstplaner.Models;

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

        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }

        public string NeueSchichtName { get; set; }
        public string NeueSchichtAbteilung { get; set; }
        public string NeueSchichtWochentag { get; set; }
        public int NeueSchichtKapazitaet { get; set; } = 2;

        private string _statusNachricht;
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

        private readonly DienstplanDataService _dataService;

        public MainViewModel()
            : this(new DienstplanDataService())
        {
        }

        public MainViewModel(DienstplanDataService dataService)
        {
            _dataService = dataService;
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);

            _dataService.SeedDemoDataIfEmpty();
            LadeDaten();
        }

        private void AddMitarbeiter(object obj)
        {
            try
            {
                _dataService.MitarbeiterHinzufuegen(NeuerMitarbeiterName, NeueMitarbeiterAbteilung, NeuerMitarbeiterQualifikation);
                LadeDaten();
                StatusNachricht = "Mitarbeiter hinzugefügt";
            }
            catch (Exception ex)
            {
                StatusNachricht = "Mitarbeiter konnte nicht gespeichert werden: " + ex.Message;
            }
        }

        private void AddSchicht(object obj)
        {
            try
            {
                _dataService.SchichtHinzufuegen(NeueSchichtName, NeueSchichtAbteilung, NeueSchichtWochentag, NeueSchichtKapazitaet);
                LadeDaten();
                StatusNachricht = "Schicht hinzugefügt";
            }
            catch (Exception ex)
            {
                StatusNachricht = "Schicht konnte nicht gespeichert werden: " + ex.Message;
            }
        }

        private void Zuweisen(object obj)
        {
            StatusNachricht = _dataService.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);
            LadeDaten();
        }

        private void LadeDaten()
        {
            MitarbeiterListe.Clear();
            foreach (Mitarbeiter mitarbeiter in _dataService.LadeMitarbeiter())
                MitarbeiterListe.Add(mitarbeiter);

            SchichtListe.Clear();
            foreach (Schicht schicht in _dataService.LadeSchichten())
                SchichtListe.Add(schicht);

            MitarbeiterView.Refresh();
            SchichtView.Refresh();
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
