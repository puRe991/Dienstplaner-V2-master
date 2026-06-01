using System;

namespace Dienstplaner.Infrastructure.Entities
{
    public class ZuweisungEntity
    {
        public Guid Id { get; set; }
        public Guid MandantId { get; set; }
        public Guid MitarbeiterId { get; set; }
        public Guid SchichtId { get; set; }
        public DateTime ErstelltAm { get; set; }
    }
}
