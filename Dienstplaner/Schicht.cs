using System;
using System.Collections.Generic;

namespace Dienstplaner.Models
{
    public class Schicht
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Abteilung { get; set; }

        public string Wochentag { get; set; }

        public DateTime Start { get; set; }
        public DateTime Ende { get; set; }

        public int BenoetigteMitarbeiter { get; set; }
        public string BenoetigteQualifikation { get; set; }

        public List<string> MitarbeiterNamen { get; set; }
        public List<int> MitarbeiterIds { get; set; }

        public Schicht()
        {
            MitarbeiterNamen = new List<string>();
            MitarbeiterIds = new List<int>();
        }

        public bool IstVoll
        {
            get { return MitarbeiterNamen.Count >= BenoetigteMitarbeiter; }
        }

        public int DauerInStunden
        {
            get { return (int)(Ende - Start).TotalHours; }
        }
    }
}