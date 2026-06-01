using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
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
        public ObservableCollection<PlanungsZeile> WochenplanZeilen { get; set; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

        public Mitarbeiter AusgewaehlterMitarbeiter { get; set; }
        public Schicht AusgewaehlteSchicht { get; set; }
        public Schicht AusgewaehlteZielSchicht { get; set; }

        // Inputs
        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }

        public string NeueSchichtName { get; set; }
        public string NeueSchichtAbteilung { get; set; }
        public string NeueSchichtWochentag { get; set; }
        public int NeueSchichtKapazitaet { get; set; } = 2;

        public string FilterFiliale { get; set; }
        public string FilterAbteilung { get; set; }
        public string FilterWoche { get; set; }
        public string FilterRolle { get; set; }
        public Mitarbeiter FilterMitarbeiter { get; set; }

        public string StatusNachricht { get; set; }

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
        public ICommand FilterAnwendenCommand { get; }
        public ICommand FilterZuruecksetzenCommand { get; }
        public ICommand SchichtKopierenCommand { get; }
        public ICommand SchichtVerschiebenCommand { get; }
        public ICommand ZuweisungenKopierenCommand { get; }
        public ICommand ZuweisungenVerschiebenCommand { get; }

        private readonly ZuweisungsService _service;

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();
            WochenplanZeilen = new ObservableCollection<PlanungsZeile>();

            MitarbeiterView = CollectionViewSource.GetDefaultView(MitarbeiterListe);
            SchichtView = CollectionViewSource.GetDefaultView(SchichtListe);
            SchichtView.Filter = FilterSchicht;

            _service = new ZuweisungsService();

            MitarbeiterHinzufuegenCommand = new RelayCommand(AddMitarbeiter);
            SchichtHinzufuegenCommand = new RelayCommand(AddSchicht);
            ZuweisenCommand = new RelayCommand(Zuweisen);
            FilterAnwendenCommand = new RelayCommand(ApplyFilter);
            FilterZuruecksetzenCommand = new RelayCommand(ResetFilter);
            SchichtKopierenCommand = new RelayCommand(CopySchicht);
            SchichtVerschiebenCommand = new RelayCommand(MoveSchicht);
            ZuweisungenKopierenCommand = new RelayCommand(CopyAssignments);
            ZuweisungenVerschiebenCommand = new RelayCommand(MoveAssignments);

            Seed();
            RefreshViews();
        }

        private void AddMitarbeiter(object obj)
        {
            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = MitarbeiterListe.Count + 1,
                Name = NeuerMitarbeiterName,
                Abteilung = NeueMitarbeiterAbteilung,
                Qualifikation = NeuerMitarbeiterQualifikation,
                Filiale = "Filiale Mitte",
                IstAktiv = true
            });

            StatusNachricht = "Mitarbeiter hinzugefügt";
            RefreshViews();
        }

        private void AddSchicht(object obj)
        {
            SchichtListe.Add(new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName,
                Abteilung = NeueSchichtAbteilung,
                Rolle = NeueSchichtAbteilung,
                Wochentag = NeueSchichtWochentag,
                Start = DateTime.Today.AddHours(8),
                Ende = DateTime.Today.AddHours(16),
                Filiale = "Filiale Mitte",
                Kalenderwoche = FilterWoche,
                BenoetigteMitarbeiter = NeueSchichtKapazitaet
            });

            StatusNachricht = "Schicht hinzugefügt";
            RefreshViews();
        }

        private void Zuweisen(object obj)
        {
            StatusNachricht = _service.Zuweisen(AusgewaehlterMitarbeiter, AusgewaehlteSchicht);
            RefreshViews();
        }

        private void ApplyFilter(object obj)
        {
            StatusNachricht = "Filter angewendet";
            RefreshViews();
        }

        private void ResetFilter(object obj)
        {
            FilterFiliale = null;
            FilterAbteilung = null;
            FilterWoche = null;
            FilterRolle = null;
            FilterMitarbeiter = null;
            StatusNachricht = "Filter zurückgesetzt";
            OnPropertyChanged(nameof(FilterFiliale));
            OnPropertyChanged(nameof(FilterAbteilung));
            OnPropertyChanged(nameof(FilterWoche));
            OnPropertyChanged(nameof(FilterRolle));
            OnPropertyChanged(nameof(FilterMitarbeiter));
            RefreshViews();
        }

        private bool FilterSchicht(object obj)
        {
            Schicht schicht = obj as Schicht;
            if (schicht == null)
                return false;

            return Contains(schicht.Filiale, FilterFiliale)
                   && Contains(schicht.Abteilung, FilterAbteilung)
                   && Contains(schicht.Kalenderwoche, FilterWoche)
                   && Contains(schicht.RolleAnzeige, FilterRolle)
                   && (FilterMitarbeiter == null || schicht.MitarbeiterNamen.Contains(FilterMitarbeiter.Name));
        }

        private static bool Contains(string value, string filter)
        {
            if (string.IsNullOrWhiteSpace(filter))
                return true;

            return (value ?? string.Empty).IndexOf(filter, StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private void CopySchicht(object obj)
        {
            if (AusgewaehlteSchicht == null)
            {
                StatusNachricht = "Keine Quellschicht ausgewählt";
                OnPropertyChanged(nameof(StatusNachricht));
                return;
            }

            SchichtListe.Add(AusgewaehlteSchicht.CloneWithoutAssignments(SchichtListe.Count + 1));
            StatusNachricht = "Schicht kopiert";
            RefreshViews();
        }

        private void MoveSchicht(object obj)
        {
            if (AusgewaehlteSchicht == null)
            {
                StatusNachricht = "Keine Schicht zum Verschieben ausgewählt";
                OnPropertyChanged(nameof(StatusNachricht));
                return;
            }

            AusgewaehlteSchicht.Wochentag = string.IsNullOrWhiteSpace(NeueSchichtWochentag)
                ? "Ungeplant"
                : NeueSchichtWochentag;
            StatusNachricht = "Schicht verschoben";
            RefreshViews();
        }

        private void CopyAssignments(object obj)
        {
            if (AusgewaehlteSchicht == null || AusgewaehlteZielSchicht == null)
            {
                StatusNachricht = "Quelle und Ziel für Zuweisungen wählen";
                OnPropertyChanged(nameof(StatusNachricht));
                return;
            }

            foreach (string name in AusgewaehlteSchicht.MitarbeiterNamen.Where(n => !AusgewaehlteZielSchicht.MitarbeiterNamen.Contains(n)).ToList())
                AusgewaehlteZielSchicht.MitarbeiterNamen.Add(name);

            StatusNachricht = "Zuweisungen kopiert";
            RefreshViews();
        }

        private void MoveAssignments(object obj)
        {
            CopyAssignments(obj);

            if (AusgewaehlteSchicht == null || AusgewaehlteZielSchicht == null)
                return;

            AusgewaehlteSchicht.MitarbeiterNamen.Clear();
            StatusNachricht = "Zuweisungen verschoben";
            RefreshViews();
        }

        private void RefreshViews()
        {
            SchichtView.Refresh();
            RebuildPlanungsZeilen();
            OnPropertyChanged(nameof(StatusNachricht));
            OnPropertyChanged(nameof(BesetzungSoll));
            OnPropertyChanged(nameof(BesetzungIst));
            OnPropertyChanged(nameof(BesetzungsDifferenz));
            OnPropertyChanged(nameof(KonfliktAnzahl));
        }


        private void RebuildPlanungsZeilen()
        {
            WochenplanZeilen.Clear();

            foreach (var roleGroup in SchichtListe.Where(s => FilterSchicht(s)).GroupBy(s => s.RolleAnzeige).OrderBy(g => g.Key))
            {
                PlanungsZeile zeile = new PlanungsZeile { Rolle = roleGroup.Key };

                foreach (Schicht schicht in roleGroup)
                {
                    switch ((schicht.Wochentag ?? string.Empty).ToLowerInvariant())
                    {
                        case "montag":
                            zeile.Montag.Add(schicht);
                            break;
                        case "dienstag":
                            zeile.Dienstag.Add(schicht);
                            break;
                        case "mittwoch":
                            zeile.Mittwoch.Add(schicht);
                            break;
                        case "donnerstag":
                            zeile.Donnerstag.Add(schicht);
                            break;
                        case "freitag":
                            zeile.Freitag.Add(schicht);
                            break;
                        case "samstag":
                            zeile.Samstag.Add(schicht);
                            break;
                        case "sonntag":
                            zeile.Sonntag.Add(schicht);
                            break;
                    }
                }

                WochenplanZeilen.Add(zeile);
            }
        }

        private void Seed()
        {
            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = 1,
                Name = "Max Mustermann",
                Abteilung = "Kasse",
                Qualifikation = "Kassenleitung",
                Filiale = "Filiale Mitte",
                WochenstundenLimit = 38,
                IstAktiv = true
            });

            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = 2,
                Name = "Erika Beispiel",
                Abteilung = "Verkauf",
                Qualifikation = "Beratung",
                Filiale = "Filiale Mitte",
                WochenstundenLimit = 30,
                IstAktiv = true
            });

            MitarbeiterListe.Add(new Mitarbeiter
            {
                Id = 3,
                Name = "Sam Lager",
                Abteilung = "Lager",
                Qualifikation = "Warenannahme",
                Filiale = "Filiale Nord",
                WochenstundenLimit = 25,
                IstAktiv = true
            });

            Schicht frueh = new Schicht
            {
                Id = 1,
                Name = "Frühschicht",
                Abteilung = "Kasse",
                Rolle = "Kassenleitung",
                Wochentag = "Montag",
                Start = DateTime.Today.AddHours(6),
                Ende = DateTime.Today.AddHours(14),
                Filiale = "Filiale Mitte",
                Kalenderwoche = "KW 23",
                BenoetigteMitarbeiter = 2,
                BenoetigteQualifikation = "Kassenleitung"
            };
            frueh.MitarbeiterNamen.Add("Max Mustermann");

            Schicht spaet = new Schicht
            {
                Id = 2,
                Name = "Spätschicht",
                Abteilung = "Verkauf",
                Rolle = "Beratung",
                Wochentag = "Mittwoch",
                Start = DateTime.Today.AddHours(14),
                Ende = DateTime.Today.AddHours(22),
                Filiale = "Filiale Mitte",
                Kalenderwoche = "KW 23",
                BenoetigteMitarbeiter = 1,
                BenoetigteQualifikation = "Beratung"
            };
            spaet.MitarbeiterNamen.Add("Erika Beispiel");

            Schicht lager = new Schicht
            {
                Id = 3,
                Name = "Warenannahme",
                Abteilung = "Lager",
                Rolle = "Warenannahme",
                Wochentag = "Freitag",
                Start = DateTime.Today.AddHours(7),
                Ende = DateTime.Today.AddHours(13),
                Filiale = "Filiale Nord",
                Kalenderwoche = "KW 23",
                BenoetigteMitarbeiter = 2,
                BenoetigteQualifikation = "Warenannahme"
            };
            lager.MitarbeiterNamen.Add("Sam Lager");

            SchichtListe.Add(frueh);
            SchichtListe.Add(spaet);
            SchichtListe.Add(lager);

            MitarbeiterListe[0].Schichten.Add(frueh);
            MitarbeiterListe[1].Schichten.Add(spaet);
            MitarbeiterListe[2].Schichten.Add(lager);

            StatusNachricht = "Planungsansicht bereit";
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }


    public class PlanungsZeile
    {
        public string Rolle { get; set; }
        public ObservableCollection<Schicht> Montag { get; } = new ObservableCollection<Schicht>();
        public ObservableCollection<Schicht> Dienstag { get; } = new ObservableCollection<Schicht>();
        public ObservableCollection<Schicht> Mittwoch { get; } = new ObservableCollection<Schicht>();
        public ObservableCollection<Schicht> Donnerstag { get; } = new ObservableCollection<Schicht>();
        public ObservableCollection<Schicht> Freitag { get; } = new ObservableCollection<Schicht>();
        public ObservableCollection<Schicht> Samstag { get; } = new ObservableCollection<Schicht>();
        public ObservableCollection<Schicht> Sonntag { get; } = new ObservableCollection<Schicht>();
    }
}
