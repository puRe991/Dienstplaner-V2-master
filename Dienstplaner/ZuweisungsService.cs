using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ZuweisungsService
    {
        private readonly AuditService _auditService;
        private readonly RollenService _rollenService;

        public ZuweisungsService(AuditService auditService, RollenService rollenService)
        {
            _auditService = auditService;
            _rollenService = rollenService;
        }

        public string Zuweisen(Mitarbeiter m, Schicht s, BenutzerKontext benutzer)
        {
            _rollenService.StellePersonenDatenZugriffSicher(benutzer, "Dienstplan ändern");

            if (m == null || s == null)
                return "Ungültige Auswahl";

            if (!m.IstAktiv)
                return "Mitarbeiter ist nicht verfügbar";

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

            var alteMitarbeiterWerte = m.ToAuditString();
            var alteSchichtWerte = s.ToAuditString();

            m.Schichten.Add(s);
            s.MitarbeiterNamen.Add(m.Name);
            m.AktuelleWochenstunden += s.DauerInStunden;

            _auditService.Protokolliere(AuditAction.DienstplanGeaendert, "Mitarbeiter", m.Id, benutzer, alteMitarbeiterWerte, m.ToAuditString(), "Schicht zugewiesen");
            _auditService.Protokolliere(AuditAction.DienstplanGeaendert, "Schicht", s.Id, benutzer, alteSchichtWerte, s.ToAuditString(), "Mitarbeiter zugewiesen");

            return "Zuweisung erfolgreich";
        }
    }
}
