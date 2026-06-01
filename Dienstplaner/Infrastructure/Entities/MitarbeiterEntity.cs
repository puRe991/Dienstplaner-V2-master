using System;

namespace Dienstplaner.Infrastructure.Entities
{
    public class MitarbeiterEntity
    {
        public Guid Id { get; set; }
        public Guid MandantId { get; set; }
        public Guid AbteilungId { get; set; }
        public string Name { get; set; }
        public int WochenstundenLimit { get; set; }
        public bool IstAktiv { get; set; }
    }
}
