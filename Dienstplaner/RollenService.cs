using System;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class RollenService
    {
        public void StellePersonenDatenZugriffSicher(BenutzerKontext benutzer, string aktion)
        {
            if (benutzer == null)
                throw new UnauthorizedAccessException("Kein Benutzerkontext vorhanden.");

            if (benutzer.Rolle == BenutzerRolle.Administrator ||
                benutzer.Rolle == BenutzerRolle.Datenschutzbeauftragter ||
                benutzer.Rolle == BenutzerRolle.Planer)
            {
                return;
            }

            throw new UnauthorizedAccessException($"Rolle {benutzer.Rolle} darf keine personenbezogenen Daten für '{aktion}' verarbeiten.");
        }

        public void StelleAdminOderDatenschutzSicher(BenutzerKontext benutzer, string aktion)
        {
            if (benutzer == null)
                throw new UnauthorizedAccessException("Kein Benutzerkontext vorhanden.");

            if (benutzer.Rolle == BenutzerRolle.Administrator || benutzer.Rolle == BenutzerRolle.Datenschutzbeauftragter)
                return;

            throw new UnauthorizedAccessException($"Rolle {benutzer.Rolle} darf die DSGVO-Funktion '{aktion}' nicht ausführen.");
        }
    }
}
