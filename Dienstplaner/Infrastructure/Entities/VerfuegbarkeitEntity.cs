using System;

namespace Dienstplaner.Infrastructure.Entities
{
    public class VerfuegbarkeitEntity
    {
        public Guid Id { get; set; }
        public Guid MandantId { get; set; }
        public Guid MitarbeiterId { get; set; }
        public DateTime Von { get; set; }
        public DateTime Bis { get; set; }
    }
}
