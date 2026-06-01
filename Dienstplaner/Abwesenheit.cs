using System;

namespace Dienstplaner.Models
{
    public class Abwesenheit
    {
        public int Id { get; set; }
        public int MitarbeiterId { get; set; }
        public string Grund { get; set; }
        public DateTime Von { get; set; }
        public DateTime Bis { get; set; }
        public bool IstBezahlt { get; set; }

        public bool Ueberschneidet(DateTime start, DateTime ende)
        {
            return Von < ende && Bis > start;
        }
    }
}
