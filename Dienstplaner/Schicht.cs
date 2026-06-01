using System;
using System.Collections.Generic;

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

        public string Wochentag { get; set; }

        public DateTime Start { get; set; }
        public DateTime Ende { get; set; }

        public int BenoetigteMitarbeiter { get; set; }
        public string BenoetigteQualifikation { get; set; }
        public decimal Pausenstunden { get; set; }
        public decimal Zuschlagsstunden { get; set; }
        public decimal Zuschlagsfaktor { get; set; }
        public string Regelhinweis { get; set; }

        public List<string> MitarbeiterNamen { get; set; }

        public Schicht()
        {
            MitarbeiterNamen = new List<string>();
            FilialeName = "Zentrale";
            Start = DateTime.Today.AddHours(8);
            Ende = DateTime.Today.AddHours(16);
            Pausenstunden = 0.5m;
            Zuschlagsfaktor = 0.25m;
        }

        public bool IstVoll
        {
            get { return MitarbeiterNamen.Count >= BenoetigteMitarbeiter; }
        }

        public int DauerInStunden
        {
            get { return (int)(Ende - Start).TotalHours; }
        }

        public string ToAuditString()
        {
            return $"Id={Id};Name={Name};Abteilung={Abteilung};Wochentag={Wochentag};Start={Start:O};Ende={Ende:O};BenoetigteMitarbeiter={BenoetigteMitarbeiter};BenoetigteQualifikation={BenoetigteQualifikation};Mitarbeiter={string.Join(",", MitarbeiterNamen)}";
        }
    }
}
