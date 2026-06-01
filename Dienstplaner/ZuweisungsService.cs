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
                return "Mitarbeiter ist inaktiv";

            if (m.MandantId != s.MandantId || m.FilialeId != s.FilialeId)
                return "Mandant oder Filiale passt nicht";

            if (s.IstVoll)
                return "Schicht ist bereits voll";

            if (m.Schichten.Any(x =>
                s.Start < x.Ende && s.Ende > x.Start))
                return "Zeitkonflikt";

            if (m.Abwesenheiten.Any(a => a.Ueberschneidet(s.Start, s.Ende)))
                return "Mitarbeiter ist abwesend";

            if (m.Iststunden + s.NettoDauerInStunden > m.WochenstundenLimit)
                return "Wochenstundenlimit würde überschritten";

            if (!string.IsNullOrEmpty(s.BenoetigteQualifikation) &&
                m.Qualifikation != s.BenoetigteQualifikation)
                return "Qualifikation passt nicht";

            m.Schichten.Add(s);
            s.MitarbeiterNamen.Add(m.Name);

            return "Zuweisung erfolgreich";
        }
    }
}
