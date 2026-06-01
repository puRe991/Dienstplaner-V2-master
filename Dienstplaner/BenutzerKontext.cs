using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class BenutzerKontext
    {
        public string Benutzername { get; set; }
        public BenutzerRolle Rolle { get; set; }

        public static BenutzerKontext StandardAdmin()
        {
            return new BenutzerKontext
            {
                Benutzername = "admin@dienstplaner.local",
                Rolle = BenutzerRolle.Administrator
            };
        }
    }
}
