using System;

namespace Dienstplaner.Models
{
    public class AuditLogEintrag
    {
        public int Id { get; set; }
        public string Aktion { get; set; }
        public string Entitaet { get; set; }
        public int EntitaetId { get; set; }
        public string Benutzer { get; set; }
        public DateTime ZeitpunktUtc { get; set; }
        public string AlteWerte { get; set; }
        public string NeueWerte { get; set; }
        public string Begruendung { get; set; }
    }
}
