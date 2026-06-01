using System;

namespace Dienstplaner.Models
{
    public class UmsatzForecast
    {
        public int FilialeId { get; set; }
        public string FilialeName { get; set; }
        public DateTime Datum { get; set; }
        public decimal ErwarteterUmsatz { get; set; }
        public int ErwarteteKundenfrequenz { get; set; }
    }
}
