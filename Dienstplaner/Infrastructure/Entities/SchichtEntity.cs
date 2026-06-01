using System;

namespace Dienstplaner.Infrastructure.Entities
{
    public class SchichtEntity
    {
        public Guid Id { get; set; }
        public Guid MandantId { get; set; }
        public Guid AbteilungId { get; set; }
        public Guid? BenoetigteQualifikationId { get; set; }
        public string Name { get; set; }
        public string Wochentag { get; set; }
        public DateTime Start { get; set; }
        public DateTime Ende { get; set; }
        public int BenoetigteMitarbeiter { get; set; }
    }
}
