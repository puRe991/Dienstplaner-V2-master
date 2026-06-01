using System;

namespace Dienstplaner.Models
{
    public class MitarbeiterAnfrage
    {
        public int Id { get; set; }
        public int MitarbeiterId { get; set; }
        public string Titel { get; set; }
        public string Status { get; set; }
        public DateTime ErstelltAm { get; set; } = DateTime.Now;
    }
}
