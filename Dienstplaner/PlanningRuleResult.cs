using System.Collections.Generic;
using System.Linq;

namespace Dienstplaner.Models
{
    public class PlanningRuleResult
    {
        public List<string> Errors { get; private set; }
        public List<string> Warnings { get; private set; }

        public PlanningRuleResult()
        {
            Errors = new List<string>();
            Warnings = new List<string>();
        }

        public bool HasErrors
        {
            get { return Errors.Any(); }
        }

        public bool HasWarnings
        {
            get { return Warnings.Any(); }
        }

        public bool IsSuccess
        {
            get { return !HasErrors; }
        }

        public void AddError(string message)
        {
            if (!string.IsNullOrWhiteSpace(message))
                Errors.Add(message);
        }

        public void AddWarning(string message)
        {
            if (!string.IsNullOrWhiteSpace(message))
                Warnings.Add(message);
        }

        public void Merge(PlanningRuleResult result)
        {
            if (result == null)
                return;

            Errors.AddRange(result.Errors);
            Warnings.AddRange(result.Warnings);
        }
    }
}
