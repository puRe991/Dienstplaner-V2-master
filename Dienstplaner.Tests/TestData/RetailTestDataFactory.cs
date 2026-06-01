using System;
using Dienstplaner.Models;

namespace Dienstplaner.Tests.TestData
{
    internal static class RetailTestDataFactory
    {
        public static Mitarbeiter KassiererVollzeit()
        {
            return new Mitarbeiter
            {
                Id = 101,
                Name = "Anna Kasse",
                Abteilung = "Kasse",
                Qualifikation = "Kasse",
                IstAktiv = true,
                WochenstundenLimit = 40,
                AktuelleWochenstunden = 0
            };
        }

        public static Mitarbeiter LagerMitarbeiter()
        {
            return new Mitarbeiter
            {
                Id = 102,
                Name = "Ben Lager",
                Abteilung = "Lager",
                Qualifikation = "Lager",
                IstAktiv = true,
                WochenstundenLimit = 40,
                AktuelleWochenstunden = 0
            };
        }

        public static Mitarbeiter TeilzeitKassierer(int aktuelleWochenstunden = 16)
        {
            return new Mitarbeiter
            {
                Id = 103,
                Name = "Clara Teilzeit",
                Abteilung = "Kasse",
                Qualifikation = "Kasse",
                IstAktiv = true,
                WochenstundenLimit = 20,
                AktuelleWochenstunden = aktuelleWochenstunden
            };
        }

        public static Mitarbeiter KrankGemeldeterKassierer()
        {
            return new Mitarbeiter
            {
                Id = 104,
                Name = "David Krank",
                Abteilung = "Kasse",
                Qualifikation = "Kasse",
                IstAktiv = false,
                WochenstundenLimit = 40
            };
        }

        public static Schicht KassenFruehschicht(int benoetigteMitarbeiter = 2)
        {
            return new Schicht
            {
                Id = 201,
                Name = "Kasse Frühschicht",
                Abteilung = "Kasse",
                Wochentag = "Montag",
                Start = new DateTime(2026, 6, 1, 8, 0, 0),
                Ende = new DateTime(2026, 6, 1, 14, 0, 0),
                BenoetigteMitarbeiter = benoetigteMitarbeiter,
                BenoetigteQualifikation = "Kasse"
            };
        }

        public static Schicht LagerSpaetschicht()
        {
            return new Schicht
            {
                Id = 202,
                Name = "Lager Spätschicht",
                Abteilung = "Lager",
                Wochentag = "Dienstag",
                Start = new DateTime(2026, 6, 2, 14, 0, 0),
                Ende = new DateTime(2026, 6, 2, 22, 0, 0),
                BenoetigteMitarbeiter = 1,
                BenoetigteQualifikation = "Lager"
            };
        }

        public static Schicht WochenendeKasse()
        {
            return new Schicht
            {
                Id = 203,
                Name = "Wochenende Kasse",
                Abteilung = "Kasse",
                Wochentag = "Samstag",
                Start = new DateTime(2026, 6, 6, 10, 0, 0),
                Ende = new DateTime(2026, 6, 6, 18, 0, 0),
                BenoetigteMitarbeiter = 2,
                BenoetigteQualifikation = "Kasse"
            };
        }

        public static Schicht FeiertagKasse()
        {
            return new Schicht
            {
                Id = 204,
                Name = "Feiertag Kasse",
                Abteilung = "Kasse",
                Wochentag = "Feiertag",
                Start = new DateTime(2026, 12, 24, 9, 0, 0),
                Ende = new DateTime(2026, 12, 24, 14, 0, 0),
                BenoetigteMitarbeiter = 3,
                BenoetigteQualifikation = "Kasse"
            };
        }
    }
}
