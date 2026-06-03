using System;
using System.Collections.Generic;
using System.Globalization;

namespace Dienstplaner.Models
{
    public class Schicht
    {
        private string _wochentag;

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
        public List<string> MitarbeiterNamen { get; set; }
        public List<int> MitarbeiterIds { get; set; }

        public Schicht()
        {
            MitarbeiterNamen = new List<string>();
            MitarbeiterIds = new List<int>();
            FilialeName = "Zentrale";
            Start = DateTime.Today.AddHours(8);
            Ende = DateTime.Today.AddHours(16);
            Pausenstunden = 0;
            Zuschlagsfaktor = 0.25m;
        }

        public string Wochentag
        {
            get { return string.IsNullOrEmpty(_wochentag) ? Start.ToString("dddd", CultureInfo.CurrentCulture) : _wochentag; }
            set { _wochentag = value; }
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

        public bool IstVoll { get { return MitarbeiterNamen.Count >= BenoetigteMitarbeiter; } }
        public decimal NettoDauerInStunden { get { return (decimal)(Ende - Start).TotalHours - Pausenstunden; } }
        public int DauerInStunden { get { return (int)NettoDauerInStunden; } }
        public int PauseInMinuten { get { return (int)(Pausenstunden * 60); } }
        public decimal Besetzungsgrad { get { return BenoetigteMitarbeiter > 0 ? (decimal)MitarbeiterNamen.Count / BenoetigteMitarbeiter : 0; } }

        public string ToAuditString()
        {
            return $"Id={Id};Name={Name};Abteilung={Abteilung};Wochentag={Wochentag};Start={Start:O};Ende={Ende:O};BenoetigteMitarbeiter={BenoetigteMitarbeiter};BenoetigteQualifikation={BenoetigteQualifikation};Mitarbeiter={string.Join(",", MitarbeiterNamen)}";
        }
    }
}
