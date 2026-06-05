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

    }
}
