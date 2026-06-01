using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ForecastImportService
    {
        public List<UmsatzForecast> ImportiereCsv(string pfad)
        {
            List<UmsatzForecast> result = new List<UmsatzForecast>();

            if (string.IsNullOrWhiteSpace(pfad) || !File.Exists(pfad))
                return result;

            string[] zeilen = File.ReadAllLines(pfad);
            for (int i = 1; i < zeilen.Length; i++)
            {
                string[] spalten = zeilen[i].Split(';');
                if (spalten.Length < 5)
                    continue;

                int filialeId;
                DateTime datum;
                decimal umsatz;
                int kunden;

                if (!int.TryParse(spalten[0], out filialeId) ||
                    !DateTime.TryParse(spalten[2], CultureInfo.GetCultureInfo("de-DE"), DateTimeStyles.None, out datum) ||
                    !decimal.TryParse(spalten[3], NumberStyles.Number, CultureInfo.GetCultureInfo("de-DE"), out umsatz) ||
                    !int.TryParse(spalten[4], out kunden))
                    continue;

                result.Add(new UmsatzForecast
                {
                    FilialeId = filialeId,
                    FilialeName = spalten[1],
                    Datum = datum,
                    ErwarteterUmsatz = umsatz,
                    ErwarteteKundenfrequenz = kunden
                });
            }

            return result;
        }
    }
}
