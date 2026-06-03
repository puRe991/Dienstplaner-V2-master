using System;
using System.Collections.Generic;
using Dienstplaner.Models;

namespace Dienstplaner.Infrastructure.Repositories
{
    public interface IDienstplanRepository
    {
        Guid EnsureMandant(string name);
        IList<Mitarbeiter> GetMitarbeiter(Guid mandantId);
        IList<Schicht> GetSchichten(Guid mandantId);
        Mitarbeiter AddMitarbeiter(Guid mandantId, string name, string abteilung, string qualifikation, int wochenstundenLimit);
        Schicht AddSchicht(Guid mandantId, string name, string abteilung, string wochentag, DateTime start, DateTime ende, int benoetigteMitarbeiter, string benoetigteQualifikation);
        string Assign(Guid mandantId, Guid mitarbeiterId, Guid schichtId);
        void DeleteSchicht(Guid mandantId, Guid schichtId);
        bool HasAnyData(Guid mandantId);
    }
}
