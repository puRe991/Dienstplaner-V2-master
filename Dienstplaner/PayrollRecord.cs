namespace Dienstplaner.Models
{
    public class PayrollRecord
    {
        public int MitarbeiterId { get; set; }
        public string MitarbeiterName { get; set; }
        public decimal Sollstunden { get; set; }
        public decimal Iststunden { get; set; }
        public decimal Pausenstunden { get; set; }
        public decimal Zuschlagsstunden { get; set; }
        public decimal Stundenlohn { get; set; }
        public decimal Grundlohn { get; set; }
        public decimal Zuschlaege { get; set; }
        public decimal Gesamtkosten { get; set; }
    }
}
