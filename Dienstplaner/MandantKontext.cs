namespace Dienstplaner.Models
{
    public class MandantKontext
    {
        public int MandantId { get; set; }
        public string MandantName { get; set; }
        public int FilialeId { get; set; }
        public string FilialeName { get; set; }
        public BenutzerRolle Rolle { get; set; }
    }
}
