using System.Collections.Generic;
using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ZuweisungsService
    {
        public string Zuweisen(Mitarbeiter m, Schicht s)
        {
            return Zuweisen(m, s, Enumerable.Empty<Availability>(), Enumerable.Empty<Absence>());
        }

        public string Zuweisen(Mitarbeiter m, Schicht s, IEnumerable<Availability> verfuegbarkeiten, IEnumerable<Absence> abwesenheiten)
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

            if (abwesenheiten != null && abwesenheiten.Any(a => a.MitarbeiterId == m.Id && a.Ueberschneidet(s)))
                return "Mitarbeiter ist für diese Schicht abwesend";

            if (verfuegbarkeiten != null)
            {
                var genehmigteVerfuegbarkeiten = verfuegbarkeiten
                    .Where(v => v.MitarbeiterId == m.Id && v.Status == RequestStatus.Approved)
                    .ToList();

                if (genehmigteVerfuegbarkeiten.Any() && !genehmigteVerfuegbarkeiten.Any(v => v.DecktSchichtAb(s)))
                    return "Mitarbeiter ist für diese Schicht nicht verfügbar";
            }

            m.Schichten.Add(s);
            s.MitarbeiterNamen.Add(m.Name);

            return "Zuweisung erfolgreich";
        }
    }
}
