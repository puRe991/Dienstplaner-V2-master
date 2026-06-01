using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class DsgvoService
    {
        private readonly RollenService _rollenService;
        private readonly AuditService _auditService;

        public DsgvoService(RollenService rollenService, AuditService auditService)
        {
            _rollenService = rollenService;
            _auditService = auditService;
        }

        public string ExportierePersonenDaten(Mitarbeiter mitarbeiter, IEnumerable<Schicht> schichten, BenutzerKontext benutzer)
        {
            _rollenService.StelleAdminOderDatenschutzSicher(benutzer, "Auskunft/Export");

            if (mitarbeiter == null)
                return "Kein Mitarbeiter für den Export ausgewählt.";

            var relevanteSchichten = schichten.Where(s => s.MitarbeiterNamen.Contains(mitarbeiter.Name)).ToList();
            var export = new StringBuilder();
            export.AppendLine("DSGVO-Auskunft");
            export.AppendLine($"MitarbeiterId: {mitarbeiter.Id}");
            export.AppendLine($"Name: {mitarbeiter.Name}");
            export.AppendLine($"Abteilung: {mitarbeiter.Abteilung}");
            export.AppendLine($"Qualifikation: {mitarbeiter.Qualifikation}");
            export.AppendLine($"Aktiv: {mitarbeiter.IstAktiv}");
            export.AppendLine("Schichten:");

            foreach (var schicht in relevanteSchichten)
                export.AppendLine($"- {schicht.Id}: {schicht.Name}, {schicht.Wochentag}, {schicht.Abteilung}");

            export.AppendLine("Audit-Einträge:");
            foreach (var audit in _auditService.Eintraege.Where(e => e.Entitaet == "Mitarbeiter" && e.EntitaetId == mitarbeiter.Id))
                export.AppendLine($"- {audit.ZeitpunktUtc:O}: {audit.Aktion} durch {audit.Benutzer}");

            _auditService.Protokolliere(AuditAction.PersonenbezogeneDatenExportiert, "Mitarbeiter", mitarbeiter.Id, benutzer, string.Empty, mitarbeiter.ToAuditString(), "DSGVO-Auskunft erstellt");
            return export.ToString();
        }

        public string BearbeiteLoeschanfrage(Mitarbeiter mitarbeiter, IEnumerable<Schicht> schichten, BenutzerKontext benutzer)
        {
            _rollenService.StelleAdminOderDatenschutzSicher(benutzer, "Löschanfrage");

            if (mitarbeiter == null)
                return "Kein Mitarbeiter für die Löschanfrage ausgewählt.";

            var alteWerte = mitarbeiter.ToAuditString();
            foreach (var schicht in schichten)
                schicht.MitarbeiterNamen.RemoveAll(n => n == mitarbeiter.Name);

            mitarbeiter.Name = $"Gelöschter Nutzer {mitarbeiter.Id}";
            mitarbeiter.Abteilung = "anonymisiert";
            mitarbeiter.Qualifikation = "anonymisiert";
            mitarbeiter.IstAktiv = false;
            mitarbeiter.Schichten.Clear();

            _auditService.Protokolliere(AuditAction.PersonenbezogeneDatenGeloescht, "Mitarbeiter", mitarbeiter.Id, benutzer, alteWerte, mitarbeiter.ToAuditString(), "DSGVO-Löschanfrage umgesetzt");
            return "Personenbezogene Daten wurden anonymisiert und Dienstplanbezüge entfernt.";
        }
    }
}
