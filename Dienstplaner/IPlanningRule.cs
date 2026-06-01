using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public interface IPlanningRule
    {
        PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht);
    }
}
