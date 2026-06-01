using System;

namespace Dienstplaner.Models
{
    public class TimeTrackingRecord
    {
        public int MitarbeiterId { get; set; }
        public string MitarbeiterName { get; set; }
        public int SchichtId { get; set; }
        public string SchichtName { get; set; }
        public DateTime GeplanterStart { get; set; }
        public DateTime GeplantesEnde { get; set; }
        public decimal GeplantePausenstunden { get; set; }
        public decimal NettoIststunden { get; set; }
        public string Kostenstelle { get; set; }
    }
}
