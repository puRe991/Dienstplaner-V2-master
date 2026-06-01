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
                s.StartUtc < x.EndUtc && s.EndUtc > x.StartUtc))
                return "Zeitkonflikt";

            if (s.DepartmentId > 0 && m.DepartmentId > 0 && m.DepartmentId != s.DepartmentId)
                return "Bereich passt nicht";

            if (s.RoleId > 0 && m.RoleId > 0 && m.RoleId != s.RoleId)
                return "Rolle passt nicht";

            if (s.RequiredSkillIds.Any() && !s.RequiredSkillIds.All(id => m.SkillIds.Contains(id)))
                return "Skills passen nicht";

            if (!string.IsNullOrEmpty(s.BenoetigteQualifikation) &&
                m.Qualifikation != s.BenoetigteQualifikation)
                return "Qualifikation passt nicht";

            m.Schichten.Add(s);
            s.MitarbeiterNamen.Add(m.Name);

            return "Zuweisung erfolgreich";
        }
    }
}
