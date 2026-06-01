using System;
using System.Collections.Generic;

namespace Dienstplaner.Models
{
    public class Schicht
    {
        public int Id { get; set; }
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

        public List<string> MitarbeiterNamen { get; set; }

        public Schicht()
        {
            MitarbeiterNamen = new List<string>();
        }

        public bool IstVoll
        {
            get { return MitarbeiterNamen.Count >= BenoetigteMitarbeiter; }
        }

        public int DauerInStunden
        {
            get { return (int)(Ende - Start).TotalHours; }
        }

        public string Zeitfenster
        {
            get { return Start.ToString("HH:mm") + " - " + Ende.ToString("HH:mm"); }
        }

        public string RolleAnzeige
        {
            get { return string.IsNullOrWhiteSpace(Rolle) ? Abteilung : Rolle; }
        }

        public int BesetzungsDifferenz
        {
            get { return MitarbeiterNamen.Count - BenoetigteMitarbeiter; }
        }

        public string Warnstatus
        {
            get
            {
                if (MitarbeiterNamen.Count == 0)
                    return "Unbesetzt";

                if (MitarbeiterNamen.Count < BenoetigteMitarbeiter)
                    return "Unterbesetzt";

                if (MitarbeiterNamen.Count > BenoetigteMitarbeiter)
                    return "Überbesetzt";

                return "OK";
            }
        }

        public string BesetzungText
        {
            get { return MitarbeiterNamen.Count + " / " + BenoetigteMitarbeiter; }
        }

        public Schicht CloneWithoutAssignments(int id)
        {
            return new Schicht
            {
                Id = id,
                Name = Name + " Kopie",
                Abteilung = Abteilung,
                Filiale = Filiale,
                Rolle = Rolle,
                Kalenderwoche = Kalenderwoche,
                Wochentag = Wochentag,
                Start = Start,
                Ende = Ende,
                BenoetigteMitarbeiter = BenoetigteMitarbeiter,
                BenoetigteQualifikation = BenoetigteQualifikation
            };
        }
    }
}
