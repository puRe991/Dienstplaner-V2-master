using System;

namespace Dienstplaner.Infrastructure.Entities
{
    public class QualifikationEntity
    {
        public Guid Id { get; set; }
        public Guid MandantId { get; set; }
        public string Name { get; set; }
    }
}
