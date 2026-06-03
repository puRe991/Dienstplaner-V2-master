using System;
using System.Collections.Generic;
using Dienstplaner.Infrastructure.Repositories;
using Dienstplaner.Models;

namespace Dienstplaner.Infrastructure.Services
{
    public class DienstplanDataService
    {
        private const string DefaultMandantName = "Standardmandant";
        private readonly IDienstplanRepository _repository;
        private readonly Guid _mandantId;

        public DienstplanDataService(IDienstplanRepository repository)
        {
            _repository = repository;
            _mandantId = _repository.EnsureMandant(DefaultMandantName);
        }

        public Guid MandantId
        {
            get { return _mandantId; }
        }

        public IList<Mitarbeiter> LadeMitarbeiter()
        {
            return _repository.GetMitarbeiter(_mandantId);
        }

        public IList<Schicht> LadeSchichten()
        {
            return _repository.GetSchichten(_mandantId);
        }

        public Mitarbeiter MitarbeiterHinzufuegen(string name, string abteilung, string qualifikation, int wochenstundenLimit)
        {
            return _repository.AddMitarbeiter(_mandantId, name, abteilung, qualifikation, wochenstundenLimit);
        }

        public Schicht SchichtHinzufuegen(string name, string abteilung, string wochentag, DateTime start, DateTime ende, int kapazitaet, string benoetigteQualifikation)
        {
            return _repository.AddSchicht(_mandantId, name, abteilung, wochentag, start, ende, kapazitaet, benoetigteQualifikation);
        }

        public string Zuweisen(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            if (mitarbeiter == null || schicht == null || mitarbeiter.DatabaseId == Guid.Empty || schicht.DatabaseId == Guid.Empty)
                return "Ungültige Auswahl";

            return _repository.Assign(_mandantId, mitarbeiter.DatabaseId, schicht.DatabaseId);
        }

        public void SchichtLoeschen(Schicht schicht)
        {
            if (schicht == null || schicht.DatabaseId == Guid.Empty)
                throw new InvalidOperationException("Die Schicht besitzt keine persistierbare Datenbank-ID.");

            _repository.DeleteSchicht(_mandantId, schicht.DatabaseId);
        }

        public void SeedDemoDataIfEmpty()
        {
#if DEBUG
            if (_repository.HasAnyData(_mandantId))
                return;

            Mitarbeiter mitarbeiter = _repository.AddMitarbeiter(_mandantId, "Max Mustermann", "Kasse", "Standard", 40);
            DateTime demoStart = GetNaechsterWochentag("Montag").Date.AddHours(8);
            Schicht schicht = _repository.AddSchicht(_mandantId, "Frühschicht", "Kasse", "Montag", demoStart, demoStart.AddHours(8), 2, "Standard");
            _repository.Assign(_mandantId, mitarbeiter.DatabaseId, schicht.DatabaseId);
#endif
        }

        private static DateTime GetNaechsterWochentag(string wochentag)
        {
            DayOfWeek target;
            if (!TryParseDayOfWeek(wochentag, out target))
                return DateTime.Today;

            int days = ((int)target - (int)DateTime.Today.DayOfWeek + 7) % 7;
            if (days == 0)
                days = 7;
            return DateTime.Today.AddDays(days);
        }

        private static bool TryParseDayOfWeek(string value, out DayOfWeek dayOfWeek)
        {
            dayOfWeek = DayOfWeek.Monday;
            if (string.IsNullOrWhiteSpace(value))
                return false;

            switch (value.Trim().ToLowerInvariant())
            {
                case "montag": dayOfWeek = DayOfWeek.Monday; return true;
                case "dienstag": dayOfWeek = DayOfWeek.Tuesday; return true;
                case "mittwoch": dayOfWeek = DayOfWeek.Wednesday; return true;
                case "donnerstag": dayOfWeek = DayOfWeek.Thursday; return true;
                case "freitag": dayOfWeek = DayOfWeek.Friday; return true;
                case "samstag": dayOfWeek = DayOfWeek.Saturday; return true;
                case "sonntag": dayOfWeek = DayOfWeek.Sunday; return true;
                default: return Enum.TryParse(value, true, out dayOfWeek);
            }
        }
    }
}
