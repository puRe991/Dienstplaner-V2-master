using System;

namespace Dienstplaner.Services
{
    public class ComplianceRichtlinie
    {
        public TimeSpan DienstplanAufbewahrung { get; } = TimeSpan.FromDays(365 * 3);
        public TimeSpan AuditAufbewahrung { get; } = TimeSpan.FromDays(365 * 10);
        public string Loeschkonzept { get; } = "Personenbezogene Dienstplandaten werden nach Ablauf der Aufbewahrung anonymisiert; Audit-Logs bleiben manipulationsgeschützt bis Fristende erhalten.";
        public string Exportkonzept { get; } = "DSGVO-Auskunft erzeugt einen maschinenlesbaren Export aller Mitarbeiter-, Schicht- und Auditdaten zur betroffenen Person.";
        public string TransportVerschluesselung { get; } = DataProtectionService.TransportSecurityRequirement;
        public string SpeicherVerschluesselung { get; } = "Sensible Exporte und Audit-Alt-/Neuwert-Felder werden mit Windows DPAPI CurrentUser verschlüsselt gespeichert.";
    }
}
