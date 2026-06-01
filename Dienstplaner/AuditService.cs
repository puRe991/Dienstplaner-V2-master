using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class AuditService
    {
        private readonly DataProtectionService _dataProtectionService;
        private int _nextId = 1;

        public ObservableCollection<AuditLogEintrag> Eintraege { get; }

        public AuditService(DataProtectionService dataProtectionService)
        {
            _dataProtectionService = dataProtectionService;
            Eintraege = new ObservableCollection<AuditLogEintrag>();
        }

        public void Protokolliere(AuditAction aktion, string entitaet, int entitaetId, BenutzerKontext benutzer, string alteWerte, string neueWerte, string begruendung)
        {
            Eintraege.Insert(0, new AuditLogEintrag
            {
                Id = _nextId++,
                Aktion = aktion.ToString(),
                Entitaet = entitaet,
                EntitaetId = entitaetId,
                Benutzer = benutzer?.Benutzername ?? "unbekannt",
                ZeitpunktUtc = DateTime.UtcNow,
                AlteWerte = _dataProtectionService.Verschluesseln(alteWerte ?? string.Empty),
                NeueWerte = _dataProtectionService.Verschluesseln(neueWerte ?? string.Empty),
                Begruendung = begruendung
            });
        }

        public void LoescheAbgelaufeneEintraege(ComplianceRichtlinie richtlinie, DateTime jetztUtc)
        {
            var abgelaufeneEintraege = Eintraege
                .Where(e => jetztUtc - e.ZeitpunktUtc > richtlinie.AuditAufbewahrung)
                .ToList();

            foreach (var eintrag in abgelaufeneEintraege)
                Eintraege.Remove(eintrag);
        }

        public string ErstelleExport()
        {
            var export = new StringBuilder();
            export.AppendLine("Id;ZeitpunktUtc;Benutzer;Aktion;Entitaet;EntitaetId;AlteWerte;NeueWerte;Begruendung");

            foreach (var eintrag in Eintraege)
            {
                export.AppendLine(string.Join(";",
                    eintrag.Id,
                    eintrag.ZeitpunktUtc.ToString("O"),
                    eintrag.Benutzer,
                    eintrag.Aktion,
                    eintrag.Entitaet,
                    eintrag.EntitaetId,
                    _dataProtectionService.Entschluesseln(eintrag.AlteWerte).Replace(";", ","),
                    _dataProtectionService.Entschluesseln(eintrag.NeueWerte).Replace(";", ","),
                    eintrag.Begruendung));
            }

            return export.ToString();
        }
    }
}
