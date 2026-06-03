using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ZuweisungsService
    {
        private readonly AuditService _auditService;
        private readonly RollenService _rollenService;

        public ZuweisungsService()
            : this(null, null)
        {
        }

        public ZuweisungsService(AuditService auditService, RollenService rollenService)
        {
            _auditService = auditService;
            _rollenService = rollenService;
        }

        public string Zuweisen(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            return Zuweisen(mitarbeiter, schicht, null);
        }

        public string Zuweisen(Mitarbeiter mitarbeiter, Schicht schicht, BenutzerKontext benutzer)
        {
            if (mitarbeiter == null || schicht == null)
                return "Ungültige Auswahl";

            if (_rollenService != null)
                _rollenService.StellePersonenDatenZugriffSicher(benutzer, "Dienstplan ändern");

            if (!mitarbeiter.IstAktiv)
                return "Mitarbeiter ist nicht verfügbar";

            if (schicht.IstVoll)
                return "Schicht ist bereits voll";

            if (mitarbeiter.Schichten.Any(x => schicht.Start < x.Ende && schicht.Ende > x.Start))
                return "Zeitkonflikt";

            if (mitarbeiter.Abwesenheiten.Any(a => a.Ueberschneidet(schicht.Start, schicht.Ende)))
                return "Mitarbeiter ist abwesend";

            if (mitarbeiter.AktuelleWochenstunden + schicht.NettoDauerInStunden > mitarbeiter.WochenstundenLimit)
                return "Wochenstundenlimit überschritten";

            if (!string.IsNullOrEmpty(schicht.BenoetigteQualifikation) &&
                mitarbeiter.Qualifikation != schicht.BenoetigteQualifikation)
                return "Qualifikation passt nicht";

            string alteMitarbeiterWerte = mitarbeiter.ToAuditString();
            string alteSchichtWerte = schicht.ToAuditString();

            mitarbeiter.Schichten.Add(schicht);
            mitarbeiter.AktuelleWochenstunden += (int)schicht.NettoDauerInStunden;
            schicht.MitarbeiterNamen.Add(mitarbeiter.Name);
            if (!schicht.MitarbeiterIds.Contains(mitarbeiter.Id))
                schicht.MitarbeiterIds.Add(mitarbeiter.Id);

            if (_auditService != null)
            {
                _auditService.Protokolliere(AuditAction.DienstplanGeaendert, "Mitarbeiter", mitarbeiter.Id, benutzer, alteMitarbeiterWerte, mitarbeiter.ToAuditString(), "Schicht zugewiesen");
                _auditService.Protokolliere(AuditAction.DienstplanGeaendert, "Schicht", schicht.Id, benutzer, alteSchichtWerte, schicht.ToAuditString(), "Mitarbeiter zugewiesen");
            }

            return "Zuweisung erfolgreich";
        }
    }
}
