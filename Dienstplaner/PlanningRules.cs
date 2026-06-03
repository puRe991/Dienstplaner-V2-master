using System;
using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class AuswahlRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter == null)
                result.AddError("Es wurde kein Mitarbeiter ausgewählt.");

            if (schicht == null)
                result.AddError("Es wurde keine Schicht ausgewählt.");

            return result;
        }
    }

    public class AktiverMitarbeiterRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter != null && !mitarbeiter.IstAktiv)
                result.AddError("Der Mitarbeiter ist nicht aktiv und darf nicht eingeplant werden.");

            return result;
        }
    }

    public class SchichtKapazitaetRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (schicht != null && schicht.IstVoll)
                result.AddError("Die Schicht ist bereits voll.");

            return result;
        }
    }

    public class WochenstundenLimitRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter == null || schicht == null || mitarbeiter.WochenstundenLimit <= 0)
                return result;

            var geplanteStunden = mitarbeiter.AktuelleWochenstunden + schicht.DauerInStunden;
            if (geplanteStunden > mitarbeiter.WochenstundenLimit)
            {
                result.AddError(string.Format(
                    "Wochenstundenlimit überschritten: {0} von maximal {1} Stunden wären geplant.",
                    geplanteStunden,
                    mitarbeiter.WochenstundenLimit));
            }

            return result;
        }
    }

    public class TageshoechstarbeitszeitRule : IPlanningRule
    {
        private const int MaxStundenProTag = 10;

        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter == null || schicht == null)
                return result;

            var stundenAmTag = mitarbeiter.Schichten
                .Where(x => x.Start.Date == schicht.Start.Date)
                .Sum(x => x.DauerInStunden) + schicht.DauerInStunden;

            if (stundenAmTag > MaxStundenProTag)
            {
                result.AddError(string.Format(
                    "Tageshöchstarbeitszeit überschritten: {0} von maximal {1} Stunden am {2:d}.",
                    stundenAmTag,
                    MaxStundenProTag,
                    schicht.Start));
            }

            return result;
        }
    }

    public class RuhezeitRule : IPlanningRule
    {
        private static readonly TimeSpan MindestRuhezeit = TimeSpan.FromHours(11);

        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter == null || schicht == null)
                return result;

            foreach (var vorhandeneSchicht in mitarbeiter.Schichten)
            {
                if (vorhandeneSchicht.Ende <= schicht.Start)
                {
                    var ruhezeit = schicht.Start - vorhandeneSchicht.Ende;
                    if (ruhezeit < MindestRuhezeit)
                    {
                        result.AddError(string.Format(
                            "Ruhezeit unterschritten: Zwischen '{0}' und '{1}' liegen nur {2:0.#} Stunden.",
                            vorhandeneSchicht.Name,
                            schicht.Name,
                            ruhezeit.TotalHours));
                    }
                }
                else if (schicht.Ende <= vorhandeneSchicht.Start)
                {
                    var ruhezeit = vorhandeneSchicht.Start - schicht.Ende;
                    if (ruhezeit < MindestRuhezeit)
                    {
                        result.AddError(string.Format(
                            "Ruhezeit unterschritten: Zwischen '{0}' und '{1}' liegen nur {2:0.#} Stunden.",
                            schicht.Name,
                            vorhandeneSchicht.Name,
                            ruhezeit.TotalHours));
                    }
                }
            }

            return result;
        }
    }

    public class PausenpflichtRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (schicht == null)
                return result;

            if (schicht.DauerInStunden > 9 && schicht.PauseInMinuten < 45)
                result.AddWarning("Für Schichten über 9 Stunden sollten mindestens 45 Minuten Pause hinterlegt sein.");
            else if (schicht.DauerInStunden > 6 && schicht.PauseInMinuten < 30)
                result.AddWarning("Für Schichten über 6 Stunden sollten mindestens 30 Minuten Pause hinterlegt sein.");

            return result;
        }
    }

    public class QualifikationRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter != null && schicht != null &&
                !string.IsNullOrWhiteSpace(schicht.BenoetigteQualifikation) &&
                !string.Equals(mitarbeiter.Qualifikation, schicht.BenoetigteQualifikation, StringComparison.OrdinalIgnoreCase))
            {
                result.AddError("Die Qualifikation des Mitarbeiters passt nicht zur Schicht.");
            }

            return result;
        }
    }

    public class AbteilungFilialeRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter == null || schicht == null)
                return result;

            if (!string.IsNullOrWhiteSpace(schicht.Abteilung) &&
                !string.Equals(mitarbeiter.Abteilung, schicht.Abteilung, StringComparison.OrdinalIgnoreCase))
            {
                result.AddError("Die Abteilung des Mitarbeiters passt nicht zur Schicht.");
            }

            if (!string.IsNullOrWhiteSpace(schicht.Filiale) &&
                !string.Equals(mitarbeiter.Filiale, schicht.Filiale, StringComparison.OrdinalIgnoreCase))
            {
                result.AddError("Die Filiale des Mitarbeiters passt nicht zur Schicht.");
            }

            return result;
        }
    }

    public class ZeitkonfliktRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter != null && schicht != null && mitarbeiter.Schichten.Any(x => schicht.Start < x.Ende && schicht.Ende > x.Start))
                result.AddError("Der Mitarbeiter hat in diesem Zeitraum bereits eine Schicht.");

            return result;
        }
    }

    public class VerfuegbarkeitAbwesenheitRule : IPlanningRule
    {
        public PlanningRuleResult Validate(Mitarbeiter mitarbeiter, Schicht schicht)
        {
            var result = new PlanningRuleResult();

            if (mitarbeiter == null || schicht == null)
                return result;

            var abwesenheit = mitarbeiter.Abwesenheiten.FirstOrDefault(x => x.Ueberschneidet(schicht));
            if (abwesenheit != null)
            {
                var grund = string.IsNullOrWhiteSpace(abwesenheit.Grund) ? "ohne Angabe" : abwesenheit.Grund;
                result.AddError(string.Format("Der Mitarbeiter ist im Schichtzeitraum abwesend ({0}).", grund));
            }

            if (mitarbeiter.Verfuegbarkeiten.Any() && !mitarbeiter.Verfuegbarkeiten.Any(x => x.DecktSchichtAb(schicht)))
                result.AddWarning("Für den Mitarbeiter ist keine passende Verfügbarkeit für diese Schicht hinterlegt.");

            return result;
        }
    }
}
