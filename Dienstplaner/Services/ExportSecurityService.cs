using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ExportSecurityService
    {
        public bool DarfExportieren(MandantKontext kontext, int mandantId, int filialeId, ExportFormat format)
        {
            if (kontext == null || kontext.MandantId != mandantId)
                return false;

            if (kontext.Rolle == BenutzerRolle.Administrator || kontext.Rolle == BenutzerRolle.Personalwesen)
                return true;

            if (kontext.Rolle == BenutzerRolle.Filialleitung && kontext.FilialeId == filialeId)
                return true;

            return false;
        }
    }
}
