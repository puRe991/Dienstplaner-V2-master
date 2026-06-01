using System.Collections.Generic;
using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class IntegrationsService
    {
        public List<PayrollRecord> ErstelleLohnabrechnung(IEnumerable<Mitarbeiter> mitarbeiter)
        {
            return mitarbeiter.Select(m =>
            {
                decimal grundlohn = m.Iststunden * m.Stundenlohn;
                decimal zuschlaege = m.Schichten.Sum(s => s.Zuschlagsstunden * m.Stundenlohn * s.Zuschlagsfaktor);

                return new PayrollRecord
                {
                    MitarbeiterId = m.Id,
                    MitarbeiterName = m.Name,
                    Sollstunden = m.SollstundenProWoche,
                    Iststunden = m.Iststunden,
                    Pausenstunden = m.Pausenstunden,
                    Zuschlagsstunden = m.Zuschlagsstunden,
                    Stundenlohn = m.Stundenlohn,
                    Grundlohn = grundlohn,
                    Zuschlaege = zuschlaege,
                    Gesamtkosten = grundlohn + zuschlaege
                };
            }).ToList();
        }

        public List<TimeTrackingRecord> ErstelleZeiterfassung(IEnumerable<Mitarbeiter> mitarbeiter)
        {
            return mitarbeiter.SelectMany(m => m.Schichten.Select(s => new TimeTrackingRecord
            {
                MitarbeiterId = m.Id,
                MitarbeiterName = m.Name,
                SchichtId = s.Id,
                SchichtName = s.Name,
                GeplanterStart = s.Start,
                GeplantesEnde = s.Ende,
                GeplantePausenstunden = s.Pausenstunden,
                NettoIststunden = s.NettoDauerInStunden,
                Kostenstelle = s.Abteilung
            })).ToList();
        }
    }
}
