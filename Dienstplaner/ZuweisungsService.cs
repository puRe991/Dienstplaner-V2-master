using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ZuweisungsService
    {
        public string Zuweisen(Mitarbeiter m, Schicht s)
        {
            if (m == null || s == null)
                return "Ungültige Auswahl";

            if (s.IstVoll)
                return "Schicht ist bereits voll";

            if (m.Schichten.Any(x =>
                s.Start < x.Ende && s.Ende > x.Start))
                return "Zeitkonflikt";

            if (!string.IsNullOrEmpty(s.BenoetigteQualifikation) &&
                m.Qualifikation != s.BenoetigteQualifikation)
                return "Qualifikation passt nicht";

            m.Schichten.Add(s);
            s.MitarbeiterNamen.Add(m.Name);

            return "Zuweisung erfolgreich";
        }
    }
}