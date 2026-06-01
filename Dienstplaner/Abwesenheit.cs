using System;

namespace Dienstplaner.Models
{
    public class Abwesenheit
    {
        public DateTime Von { get; set; }
        public DateTime Bis { get; set; }
        public string Grund { get; set; }

        public bool Ueberschneidet(Schicht schicht)
        {
            return schicht != null && schicht.Start < Bis && schicht.Ende > Von;
        }
    }
}
