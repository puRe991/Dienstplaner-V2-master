using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class DienstplanExportService
    {
        private readonly ExportSecurityService _security = new ExportSecurityService();

        public string ExportiereDienstplan(IEnumerable<Schicht> schichten, MandantKontext kontext, ExportFormat format, string zielOrdner)
        {
            List<Schicht> erlaubteSchichten = schichten
                .Where(s => _security.DarfExportieren(kontext, s.MandantId, s.FilialeId, format))
                .ToList();

            if (!erlaubteSchichten.Any())
                return "Kein Export: Rolle oder Mandant hat keine Berechtigung für die ausgewählten Dienstpläne.";

            if (!Directory.Exists(zielOrdner))
                Directory.CreateDirectory(zielOrdner);

            string basisName = "Dienstplan_" + kontext.MandantName + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string pfad;

            if (format == ExportFormat.Csv)
            {
                pfad = Path.Combine(zielOrdner, basisName + ".csv");
                File.WriteAllText(pfad, ErstelleCsv(erlaubteSchichten), Encoding.UTF8);
            }
            else if (format == ExportFormat.Excel)
            {
                pfad = Path.Combine(zielOrdner, basisName + ".xls");
                File.WriteAllText(pfad, ErstelleExcelHtml(erlaubteSchichten), Encoding.UTF8);
            }
            else
            {
                pfad = Path.Combine(zielOrdner, basisName + ".pdf");
                File.WriteAllBytes(pfad, ErstellePdf(erlaubteSchichten));
            }

            return "Export erstellt: " + pfad;
        }

        private string ErstelleCsv(IEnumerable<Schicht> schichten)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("Mandant;Filiale;Schicht;Abteilung;Wochentag;Start;Ende;Bedarf;Besetzt;Pause;Zuschlag;Mitarbeiter");
            foreach (Schicht s in schichten)
            {
                sb.AppendLine(string.Join(";", new[]
                {
                    s.MandantId.ToString(),
                    Escape(s.FilialeName),
                    Escape(s.Name),
                    Escape(s.Abteilung),
                    Escape(s.Wochentag),
                    s.Start.ToString("g", CultureInfo.GetCultureInfo("de-DE")),
                    s.Ende.ToString("g", CultureInfo.GetCultureInfo("de-DE")),
                    s.BenoetigteMitarbeiter.ToString(),
                    s.MitarbeiterNamen.Count.ToString(),
                    s.Pausenstunden.ToString(CultureInfo.GetCultureInfo("de-DE")),
                    s.Zuschlagsstunden.ToString(CultureInfo.GetCultureInfo("de-DE")),
                    Escape(string.Join(", ", s.MitarbeiterNamen))
                }));
            }
            return sb.ToString();
        }

        private string ErstelleExcelHtml(IEnumerable<Schicht> schichten)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("<html><head><meta charset=\"utf-8\" /></head><body><table border=\"1\">");
            sb.AppendLine("<tr><th>Mandant</th><th>Filiale</th><th>Schicht</th><th>Abteilung</th><th>Start</th><th>Ende</th><th>Bedarf</th><th>Besetzt</th><th>Pause</th><th>Zuschlag</th><th>Mitarbeiter</th></tr>");
            foreach (Schicht s in schichten)
            {
                sb.AppendLine("<tr><td>" + s.MandantId + "</td><td>" + Html(s.FilialeName) + "</td><td>" + Html(s.Name) + "</td><td>" + Html(s.Abteilung) + "</td><td>" + s.Start.ToString("g") + "</td><td>" + s.Ende.ToString("g") + "</td><td>" + s.BenoetigteMitarbeiter + "</td><td>" + s.MitarbeiterNamen.Count + "</td><td>" + s.Pausenstunden + "</td><td>" + s.Zuschlagsstunden + "</td><td>" + Html(string.Join(", ", s.MitarbeiterNamen)) + "</td></tr>");
            }
            sb.AppendLine("</table></body></html>");
            return sb.ToString();
        }

        private byte[] ErstellePdf(IEnumerable<Schicht> schichten)
        {
            List<string> zeilen = new List<string>();
            zeilen.Add("Dienstplan Export");
            foreach (Schicht s in schichten)
            {
                zeilen.Add(s.Start.ToString("dd.MM.yyyy HH:mm") + " - " + s.Ende.ToString("HH:mm") + " | " + s.FilialeName + " | " + s.Name + " | " + string.Join(", ", s.MitarbeiterNamen));
            }

            string textStream = "BT /F1 11 Tf 40 800 Td ";
            for (int i = 0; i < zeilen.Count; i++)
            {
                if (i > 0)
                    textStream += "0 -16 Td ";
                textStream += "(" + PdfEscape(zeilen[i]) + ") Tj ";
            }
            textStream += "ET";

            List<string> objekte = new List<string>();
            objekte.Add("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n");
            objekte.Add("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n");
            objekte.Add("3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n");
            objekte.Add("4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n");
            objekte.Add("5 0 obj << /Length " + Encoding.ASCII.GetByteCount(textStream) + " >> stream\n" + textStream + "\nendstream endobj\n");

            MemoryStream ms = new MemoryStream();
            StreamWriter writer = new StreamWriter(ms, Encoding.ASCII);
            List<long> offsets = new List<long>();
            writer.Write("%PDF-1.4\n");
            writer.Flush();
            foreach (string objekt in objekte)
            {
                offsets.Add(ms.Position);
                writer.Write(objekt);
                writer.Flush();
            }

            long xref = ms.Position;
            writer.Write("xref\n0 " + (objekte.Count + 1) + "\n0000000000 65535 f \n");
            foreach (long offset in offsets)
                writer.Write(offset.ToString("0000000000") + " 00000 n \n");
            writer.Write("trailer << /Size " + (objekte.Count + 1) + " /Root 1 0 R >>\nstartxref\n" + xref + "\n%%EOF");
            writer.Flush();
            return ms.ToArray();
        }

        private string Escape(string wert)
        {
            if (wert == null)
                return string.Empty;
            if (wert.Contains(";") || wert.Contains("\"") || wert.Contains("\n"))
                return "\"" + wert.Replace("\"", "\"\"") + "\"";
            return wert;
        }

        private string Html(string wert)
        {
            if (wert == null)
                return string.Empty;
            return wert.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace("\"", "&quot;");
        }

        private string PdfEscape(string wert)
        {
            if (wert == null)
                return string.Empty;
            return wert.Replace("\\", "\\\\").Replace("(", "\\(").Replace(")", "\\)");
        }
    }
}
