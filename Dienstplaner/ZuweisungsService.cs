using System.Collections.Generic;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ZuweisungsService
    {
        private readonly IList<IPlanningRule> _rules;

        public ZuweisungsService()
            : this(new IPlanningRule[]
            {
                new AuswahlRule(),
                new AktiverMitarbeiterRule(),
                new SchichtKapazitaetRule(),
                new WochenstundenLimitRule(),
                new TageshoechstarbeitszeitRule(),
                new RuhezeitRule(),
                new PausenpflichtRule(),
                new QualifikationRule(),
                new AbteilungFilialeRule(),
                new ZeitkonfliktRule(),
                new VerfuegbarkeitAbwesenheitRule()
            })
        {
        }

        public ZuweisungsService(IEnumerable<IPlanningRule> rules)
        {
            _rules = new List<IPlanningRule>(rules);
        }

        public PlanningRuleResult Zuweisen(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = Validate(mitarbeiter, schicht);

            if (result.HasErrors)
                return result;

            mitarbeiter.Schichten.Add(schicht);
            mitarbeiter.AktuelleWochenstunden += schicht.DauerInStunden;
            schicht.MitarbeiterNamen.Add(mitarbeiter.Name);

            return result;
        }

        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            foreach (var rule in _rules)
                result.Merge(rule.Validate(mitarbeiter, schicht));

            return result;
        }
    }
}
