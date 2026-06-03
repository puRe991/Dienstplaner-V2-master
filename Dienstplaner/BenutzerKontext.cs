using System.Security.Principal;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class BenutzerKontext
    {
        public string Benutzername { get; set; }
        public BenutzerRolle Rolle { get; set; }

        public static BenutzerKontext FuerAktuellenWindowsBenutzer()
        {
            var identitaet = WindowsIdentity.GetCurrent();
            return new BenutzerKontext
            {
                Benutzername = identitaet.Name,
                Rolle = BenutzerRolle.Planer
            };
        }

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
