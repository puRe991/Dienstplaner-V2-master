using System;

namespace Dienstplaner.Models
{
    public class Zuweisung
    {
        public Guid Id { get; set; }

        public Guid MitarbeiterId { get; set; }
        public Guid SchichtId { get; set; }

        public DateTime ErstelltAm { get; set; } = DateTime.Now;
    }
}