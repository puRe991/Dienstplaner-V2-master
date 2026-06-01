using System.Collections.Generic;

namespace Dienstplaner.Models
{
    public class Mitarbeiter
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Abteilung { get; set; }
        public string Qualifikation { get; set; }
        public string Filiale { get; set; }

        public int WochenstundenLimit { get; set; }
        public bool IstAktiv { get; set; }

        public int AktuelleWochenstunden { get; set; }

        public List<Schicht> Schichten { get; set; }
        public List<Verfuegbarkeit> Verfuegbarkeiten { get; set; }
        public List<Abwesenheit> Abwesenheiten { get; set; }

        public Mitarbeiter()
        {
            Schichten = new List<Schicht>();
            Verfuegbarkeiten = new List<Verfuegbarkeit>();
            Abwesenheiten = new List<Abwesenheit>();
        }
    }
}
