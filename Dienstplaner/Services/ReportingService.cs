using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ReportingService
    {
        public List<ReportKennzahl> ErstelleReports(IEnumerable<Mitarbeiter> mitarbeiter, IEnumerable<Schicht> schichten)
        {
            List<Mitarbeiter> mitarbeiterListe = mitarbeiter.ToList();
            List<Schicht> schichtListe = schichten.ToList();
            List<ReportKennzahl> reports = new List<ReportKennzahl>();
            CultureInfo culture = CultureInfo.GetCultureInfo("de-DE");

            decimal personalkosten = mitarbeiterListe.Sum(m => m.Schichten.Sum(s => s.NettoDauerInStunden * m.Stundenlohn + s.Zuschlagsstunden * m.Stundenlohn * s.Zuschlagsfaktor));
            decimal besetzungsgrad = schichtListe.Any() ? schichtListe.Average(s => s.Besetzungsgrad) * 100 : 0;
            decimal ueberstunden = mitarbeiterListe.Sum(m => m.Ueberstunden);
            int regelverstoesse = ZaehleRegelverstoesse(mitarbeiterListe, schichtListe);

            reports.Add(new ReportKennzahl { Kategorie = "Kosten", Name = "Personalkosten", Wert = personalkosten.ToString("C", culture), Hinweis = "Iststunden inkl. Zuschläge" });
            reports.Add(new ReportKennzahl { Kategorie = "Planung", Name = "Besetzungsgrad", Wert = besetzungsgrad.ToString("0.0", culture) + " %", Hinweis = "Zugewiesene im Verhältnis zum Bedarf" });
            reports.Add(new ReportKennzahl { Kategorie = "Arbeitszeit", Name = "Überstunden", Wert = ueberstunden.ToString("0.0", culture) + " h", Hinweis = "Iststunden über Sollstunden" });
            reports.Add(new ReportKennzahl { Kategorie = "Compliance", Name = "Regelverstöße", Wert = regelverstoesse.ToString(culture), Hinweis = "Unterbesetzung, Limits, Abwesenheiten" });

            return reports;
        }

        public int ZaehleRegelverstoesse(IEnumerable<Mitarbeiter> mitarbeiter, IEnumerable<Schicht> schichten)
        {
            int verstoesse = schichten.Count(s => s.MitarbeiterNamen.Count < s.BenoetigteMitarbeiter);

            foreach (Mitarbeiter m in mitarbeiter)
            {
                if (m.Iststunden > m.WochenstundenLimit)
                    verstoesse++;

                foreach (Schicht s in m.Schichten)
                {
                    if (m.Abwesenheiten.Any(a => a.Ueberschneidet(s.Start, s.Ende)))
                        verstoesse++;
                }
            }

            return verstoesse;
        }
    }
}
