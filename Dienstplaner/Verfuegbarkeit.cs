using System;

namespace Dienstplaner.Models
{
    public class Verfuegbarkeit
    {
        public DateTime Von { get; set; }
        public DateTime Bis { get; set; }
        public string Hinweis { get; set; }

        public bool DecktAb(Schicht schicht)
        {
            return schicht != null && Von <= schicht.Start && Bis >= schicht.Ende;
        }
    }
}
