using System;
using System.Collections.Generic;
using System.Globalization;

namespace Dienstplaner.Models
{
    public class Schicht
    {
        public int Id { get; set; }
        public int MandantId { get; set; }
        public int FilialeId { get; set; }
        public string FilialeName { get; set; }
        public string Name { get; set; }
        public string Abteilung { get; set; }
        public string Filiale { get; set; }
        public string Rolle { get; set; }
        public string Kalenderwoche { get; set; }

        public int StoreId { get; set; }
        public int DepartmentId { get; set; }
        public int RoleId { get; set; }

        public DateTime StartUtc { get; set; }
        public DateTime EndUtc { get; set; }
        public TimeSpan BreakDuration { get; set; }

        public int BenoetigteMitarbeiter { get; set; }
        public string BenoetigteQualifikation { get; set; }
        public decimal Pausenstunden { get; set; }
        public decimal Zuschlagsstunden { get; set; }
        public decimal Zuschlagsfaktor { get; set; }
        public string Regelhinweis { get; set; }

        public List<Besetzungsfenster> Besetzungsfenster { get; set; }
        public List<string> MitarbeiterNamen { get; set; }
        public List<int> MitarbeiterIds { get; set; }

        public SchichtVorlage Vorlage { get; set; }

        public Schicht()
        {
            RequiredSkillIds = new List<int>();
            Besetzungsfenster = new List<Besetzungsfenster>();
            MitarbeiterNamen = new List<string>();
            FilialeName = "Zentrale";
            Start = DateTime.Today.AddHours(8);
            Ende = DateTime.Today.AddHours(16);
            Pausenstunden = 0.5m;
            Zuschlagsfaktor = 0.25m;
        }

        public string Abteilung
        {
            get { return DepartmentId > 0 ? DepartmentId.ToString(CultureInfo.InvariantCulture) : string.Empty; }
            set
            {
                int parsed;
                DepartmentId = int.TryParse(value, out parsed) ? parsed : 0;
            }
        }

        public string Wochentag
        {
            get { return StartUtc == default(DateTime) ? string.Empty : StartUtc.ToLocalTime().ToString("dddd", CultureInfo.CurrentCulture); }
        }

        public DateTime Start
        {
            get { return StartUtc == default(DateTime) ? default(DateTime) : StartUtc.ToLocalTime(); }
            set { StartUtc = DateTime.SpecifyKind(value, DateTimeKind.Local).ToUniversalTime(); }
        }

        public DateTime Ende
        {
            get { return EndUtc == default(DateTime) ? default(DateTime) : EndUtc.ToLocalTime(); }
            set { EndUtc = DateTime.SpecifyKind(value, DateTimeKind.Local).ToUniversalTime(); }
        }

        public int BenoetigteMitarbeiter
        {
            get { return RequiredHeadcount; }
            set { RequiredHeadcount = value; }
        }

        public string BenoetigteQualifikation { get; set; }

        public bool IstVoll
        {
            get { return MitarbeiterNamen.Count >= RequiredHeadcount; }
        }

        public int DauerInStunden
        {
            get { return (int)(EndUtc - StartUtc - BreakDuration).TotalHours; }
        }

        public string ZeitraumAnzeige
        {
            get
            {
                if (StartUtc == default(DateTime) || EndUtc == default(DateTime))
                    return string.Empty;

                return string.Format(CultureInfo.CurrentCulture, "{0:g} - {1:t}", StartUtc.ToLocalTime(), EndUtc.ToLocalTime());
            }
        }

        public string BesetzungAnzeige
        {
            get { return string.Format(CultureInfo.CurrentCulture, "Ist {0} / Soll {1}", MitarbeiterNamen.Count, RequiredHeadcount); }
        }
    }

    public class SchichtVorlage
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public int StoreId { get; set; }
        public int DepartmentId { get; set; }
        public int RoleId { get; set; }
        public DayOfWeek Wochentag { get; set; }
        public TimeSpan Startzeit { get; set; }
        public TimeSpan Endzeit { get; set; }
        public TimeSpan BreakDuration { get; set; }
        public List<int> RequiredSkillIds { get; set; }
        public int RequiredHeadcount { get; set; }
        public string CostCenter { get; set; }
        public Wiederholungsregel Wiederholung { get; set; }
        public List<Besetzungsfenster> Besetzungsfenster { get; set; }

        public SchichtVorlage()
        {
            RequiredSkillIds = new List<int>();
            Wiederholung = new Wiederholungsregel();
            Besetzungsfenster = new List<Besetzungsfenster>();
        }

        public Schicht ErzeugeSchicht(DateTime datum, int id)
        {
            DateTime startLocal = datum.Date.Add(Startzeit);
            DateTime endLocal = datum.Date.Add(Endzeit);

            if (endLocal <= startLocal)
                endLocal = endLocal.AddDays(1);

            return new Schicht
            {
                Id = id,
                Name = Name,
                StoreId = StoreId,
                DepartmentId = DepartmentId,
                RoleId = RoleId,
                Start = startLocal,
                Ende = endLocal,
                BreakDuration = BreakDuration,
                RequiredSkillIds = new List<int>(RequiredSkillIds),
                RequiredHeadcount = RequiredHeadcount,
                CostCenter = CostCenter,
                Vorlage = this,
                Besetzungsfenster = KopiereBesetzungsfenster(Besetzungsfenster)
            };
        }

        private static List<Besetzungsfenster> KopiereBesetzungsfenster(IEnumerable<Besetzungsfenster> fenster)
        {
            var kopie = new List<Besetzungsfenster>();
            foreach (var eintrag in fenster)
            {
                kopie.Add(new Besetzungsfenster
                {
                    Von = eintrag.Von,
                    Bis = eintrag.Bis,
                    Mindestbesetzung = eintrag.Mindestbesetzung,
                    Sollbesetzung = eintrag.Sollbesetzung,
                    Maximalbesetzung = eintrag.Maximalbesetzung
                });
            }

            return kopie;
        }

        public string ToAuditString()
        {
            return $"Id={Id};Name={Name};Abteilung={Abteilung};Wochentag={Wochentag};Start={Start:O};Ende={Ende:O};BenoetigteMitarbeiter={BenoetigteMitarbeiter};BenoetigteQualifikation={BenoetigteQualifikation};Mitarbeiter={string.Join(",", MitarbeiterNamen)}";
        }
    }
}
