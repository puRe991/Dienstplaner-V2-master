using System;

namespace Dienstplaner.Infrastructure.Entities
{
    public class MandantEntity
    {
        public Guid Id { get; set; }
        public string Name { get; set; }
        public bool IstAktiv { get; set; }
    }
}
