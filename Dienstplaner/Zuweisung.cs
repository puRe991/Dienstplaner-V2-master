using System;

namespace Dienstplaner.Models
{
    public class Zuweisung
    {
        public int Id { get; set; }

        public int MitarbeiterId { get; set; }
        public int SchichtId { get; set; }

        public DateTime ErstelltAm { get; set; } = DateTime.Now;
    }
}