using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Globalization;
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
        public ObservableCollection<SchichtVorlage> SchichtVorlagen { get; set; }
        public ObservableCollection<Oeffnungszeiten> OeffnungszeitenListe { get; set; }
        public ObservableCollection<Sonderoeffnung> Sonderoeffnungen { get; set; }
        public ObservableCollection<Feiertag> Feiertage { get; set; }
        public ObservableCollection<VerkaufsoffenerSonntag> VerkaufsoffeneSonntage { get; set; }

        public ICollectionView MitarbeiterView { get; }
        public ICollectionView SchichtView { get; }

        public Mitarbeiter AusgewaehlterMitarbeiter { get; set; }
        public Schicht AusgewaehlteSchicht { get; set; }

        // Inputs
        public string NeuerMitarbeiterName { get; set; }
        public string NeueMitarbeiterAbteilung { get; set; }
        public string NeuerMitarbeiterQualifikation { get; set; }

        public string NeueSchichtName { get; set; }
        public int NeueSchichtStoreId { get; set; } = 1;
        public int NeueSchichtDepartmentId { get; set; } = 1;
        public int NeueSchichtRoleId { get; set; } = 1;
        public DateTime NeueSchichtDatum { get; set; } = DateTime.Today;
        public string NeueSchichtStartzeit { get; set; } = "08:00";
        public string NeueSchichtEndzeit { get; set; } = "16:00";
        public int NeueSchichtPauseMinuten { get; set; } = 30;
        public int NeueSchichtKapazitaet { get; set; } = 2;
        public int NeueSchichtMindestbesetzung { get; set; } = 1;
        public int NeueSchichtSollbesetzung { get; set; } = 2;
        public int NeueSchichtMaximalbesetzung { get; set; } = 3;
        public string NeueSchichtRequiredSkillIds { get; set; }
        public string NeueSchichtCostCenter { get; set; }
        public bool NeueSchichtAlsWoechentlicheVorlage { get; set; } = true;

        public string StatusNachricht { get; set; }

        public ICommand MitarbeiterHinzufuegenCommand { get; }
        public ICommand SchichtHinzufuegenCommand { get; }
        public ICommand ZuweisenCommand { get; }

        private readonly ZuweisungsService _service;

        public MainViewModel()
        {
            MitarbeiterListe = new ObservableCollection<Mitarbeiter>();
            SchichtListe = new ObservableCollection<Schicht>();
            SchichtVorlagen = new ObservableCollection<SchichtVorlage>();
            OeffnungszeitenListe = new ObservableCollection<Oeffnungszeiten>();
            Sonderoeffnungen = new ObservableCollection<Sonderoeffnung>();
            Feiertage = new ObservableCollection<Feiertag>();
            VerkaufsoffeneSonntage = new ObservableCollection<VerkaufsoffenerSonntag>();

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
                DepartmentId = ParseIntOrZero(NeueMitarbeiterAbteilung),
                Qualifikation = NeuerMitarbeiterQualifikation,
                SkillIds = ParseSkillIds(NeuerMitarbeiterQualifikation),
                IstAktiv = true
            });

            SetStatus("Mitarbeiter hinzugefügt");
        }

        private void AddSchicht(object obj)
        {
            TimeSpan startzeit;
            TimeSpan endzeit;

            if (!TimeSpan.TryParse(NeueSchichtStartzeit, CultureInfo.CurrentCulture, out startzeit) ||
                !TimeSpan.TryParse(NeueSchichtEndzeit, CultureInfo.CurrentCulture, out endzeit))
            {
                SetStatus("Start- oder Endzeit ist ungültig. Bitte HH:mm verwenden.");
                return;
            }

            DateTime startLocal = NeueSchichtDatum.Date.Add(startzeit);
            DateTime endLocal = NeueSchichtDatum.Date.Add(endzeit);

            if (endLocal <= startLocal)
                endLocal = endLocal.AddDays(1);

            var besetzungsfenster = new Besetzungsfenster
            {
                Von = startzeit,
                Bis = endzeit,
                Mindestbesetzung = NeueSchichtMindestbesetzung,
                Sollbesetzung = NeueSchichtSollbesetzung,
                Maximalbesetzung = NeueSchichtMaximalbesetzung
            };

            var schicht = new Schicht
            {
                Id = SchichtListe.Count + 1,
                Name = NeueSchichtName,
                StoreId = NeueSchichtStoreId,
                DepartmentId = NeueSchichtDepartmentId,
                RoleId = NeueSchichtRoleId,
                Start = startLocal,
                Ende = endLocal,
                BreakDuration = TimeSpan.FromMinutes(NeueSchichtPauseMinuten),
                RequiredHeadcount = NeueSchichtKapazitaet,
                RequiredSkillIds = ParseSkillIds(NeueSchichtRequiredSkillIds),
                CostCenter = NeueSchichtCostCenter
            };
            schicht.Besetzungsfenster.Add(besetzungsfenster);

            SchichtListe.Add(schicht);

            if (NeueSchichtAlsWoechentlicheVorlage)
            {
                SchichtVorlagen.Add(new SchichtVorlage
                {
                    Id = SchichtVorlagen.Count + 1,
                    Name = NeueSchichtName,
                    StoreId = NeueSchichtStoreId,
                    DepartmentId = NeueSchichtDepartmentId,
                    RoleId = NeueSchichtRoleId,
                    Wochentag = NeueSchichtDatum.DayOfWeek,
                    Startzeit = startzeit,
                    Endzeit = endzeit,
                    BreakDuration = TimeSpan.FromMinutes(NeueSchichtPauseMinuten),
                    RequiredHeadcount = NeueSchichtKapazitaet,
                    RequiredSkillIds = ParseSkillIds(NeueSchichtRequiredSkillIds),
                    CostCenter = NeueSchichtCostCenter,
                    Besetzungsfenster = new List<Besetzungsfenster> { besetzungsfenster }
                });
            }

            SetStatus("Schicht mit Datum/Zeit hinzugefügt");
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
                DepartmentId = 1,
                RoleId = 1,
                Qualifikation = "Standard",
                SkillIds = new List<int> { 1 }
            });

            for (int day = 1; day <= 6; day++)
            {
                OeffnungszeitenListe.Add(new Oeffnungszeiten
                {
                    StoreId = 1,
                    Wochentag = (DayOfWeek)day,
                    OeffnetUm = new TimeSpan(8, 0, 0),
                    SchliesstUm = new TimeSpan(20, 0, 0),
                    IstGeschlossen = false
                });
            }

            Feiertage.Add(new Feiertag
            {
                Datum = new DateTime(DateTime.Today.Year, 12, 25),
                Name = "1. Weihnachtsfeiertag",
                Bundesland = "bundesweit",
                Arbeitsfrei = true
            });

            VerkaufsoffeneSonntage.Add(new VerkaufsoffenerSonntag
            {
                StoreId = 1,
                Datum = DateTime.Today.AddDays(((int)DayOfWeek.Sunday - (int)DateTime.Today.DayOfWeek + 7) % 7),
                OeffnetUm = new TimeSpan(13, 0, 0),
                SchliesstUm = new TimeSpan(18, 0, 0),
                Anlass = "Innenstadtfest"
            });

            SchichtListe.Add(new Schicht
            {
                Id = 1,
                Name = "Frühschicht",
                StoreId = 1,
                DepartmentId = 1,
                RoleId = 1,
                Start = DateTime.Today.AddHours(8),
                Ende = DateTime.Today.AddHours(14),
                BreakDuration = TimeSpan.FromMinutes(30),
                RequiredHeadcount = 2,
                RequiredSkillIds = new List<int> { 1 },
                CostCenter = "KASSE-01",
                Besetzungsfenster = new List<Besetzungsfenster>
                {
                    new Besetzungsfenster
                    {
                        Von = new TimeSpan(8, 0, 0),
                        Bis = new TimeSpan(14, 0, 0),
                        Mindestbesetzung = 1,
                        Sollbesetzung = 2,
                        Maximalbesetzung = 3
                    }
                }
            });
        }

        private static List<int> ParseSkillIds(string skillIds)
        {
            if (string.IsNullOrWhiteSpace(skillIds))
                return new List<int>();

            return skillIds
                .Split(new[] { ',', ';', ' ' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(ParseIntOrZero)
                .Where(id => id > 0)
                .ToList();
        }

        private static int ParseIntOrZero(string value)
        {
            int parsed;
            return int.TryParse(value, out parsed) ? parsed : 0;
        }

        private void SetStatus(string status)
        {
            StatusNachricht = status;
            OnPropertyChanged(nameof(StatusNachricht));
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string n = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
    }
}
