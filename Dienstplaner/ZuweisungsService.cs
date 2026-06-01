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

            if (!m.IstAktiv)
                return "Mitarbeiter ist nicht verfügbar";

            if (s.IstVoll)
                return "Schicht ist bereits voll";

            if (m.Schichten.Any(x =>
                s.Start < x.Ende && s.Ende > x.Start))
                return "Zeitkonflikt";

            if (!string.IsNullOrEmpty(s.BenoetigteQualifikation) &&
                m.Qualifikation != s.BenoetigteQualifikation)
                return "Qualifikation passt nicht";

            if (m.WochenstundenLimit > 0 &&
                m.AktuelleWochenstunden + s.DauerInStunden > m.WochenstundenLimit)
                return "Wochenstundenlimit überschritten";

            m.Schichten.Add(s);
            s.MitarbeiterNamen.Add(m.Name);
            m.AktuelleWochenstunden += s.DauerInStunden;

            return "Zuweisung erfolgreich";
        }
    }
}