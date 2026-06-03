using System.Threading;
using Dienstplaner.Services;
using Dienstplaner.ViewModels;
using NUnit.Framework;

namespace Dienstplaner.Tests
{
    [TestFixture]
    [Apartment(ApartmentState.STA)]
    public class MainViewModelValidationTests
    {
        [Test]
        public void MitarbeiterHinzufuegenCommand_DoesNotAddEmployee_WhenNameIsMissing()
        {
            var viewModel = new MainViewModel
            {
                AktuellerBenutzer = BenutzerKontext.StandardAdmin(),
                NeuerMitarbeiterName = "  ",
                NeueMitarbeiterAbteilung = "Kasse",
                NeuerMitarbeiterQualifikation = "Kasse"
            };
            var initialCount = viewModel.MitarbeiterListe.Count;

            viewModel.MitarbeiterHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.MitarbeiterListe, Has.Count.EqualTo(initialCount));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Mitarbeitername ist erforderlich"));
        }

        [Test]
        public void MitarbeiterHinzufuegenCommand_DoesNotAddEmployee_WhenDepartmentIsMissing()
        {
            var viewModel = new MainViewModel
            {
                AktuellerBenutzer = BenutzerKontext.StandardAdmin(),
                NeuerMitarbeiterName = "Eva Retail",
                NeueMitarbeiterAbteilung = " ",
                NeuerMitarbeiterQualifikation = "Kasse"
            };
            var initialCount = viewModel.MitarbeiterListe.Count;

            viewModel.MitarbeiterHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.MitarbeiterListe, Has.Count.EqualTo(initialCount));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Mitarbeiterabteilung ist erforderlich"));
        }

        [Test]
        public void MitarbeiterHinzufuegenCommand_AddsTrimmedEmployee_WhenInputIsValid()
        {
            var viewModel = new MainViewModel
            {
                AktuellerBenutzer = BenutzerKontext.StandardAdmin(),
                NeuerMitarbeiterName = "  Eva Retail  ",
                NeueMitarbeiterAbteilung = "  Kasse ",
                NeuerMitarbeiterQualifikation = " Kasse "
            };
            var initialCount = viewModel.MitarbeiterListe.Count;

            viewModel.MitarbeiterHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.MitarbeiterListe, Has.Count.EqualTo(initialCount + 1));
            Assert.That(viewModel.MitarbeiterListe[initialCount].Name, Is.EqualTo("Eva Retail"));
            Assert.That(viewModel.MitarbeiterListe[initialCount].Abteilung, Is.EqualTo("Kasse"));
            Assert.That(viewModel.MitarbeiterListe[initialCount].Qualifikation, Is.EqualTo("Kasse"));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Mitarbeiter hinzugefügt"));
        }

        [Test]
        public void SchichtHinzufuegenCommand_DoesNotAddShift_WhenCapacityIsZero()
        {
            var viewModel = new MainViewModel
            {
                AktuellerBenutzer = BenutzerKontext.StandardAdmin(),
                NeueSchichtName = "Kasse Abend",
                NeueSchichtAbteilung = "Kasse",
                NeueSchichtWochentag = "Freitag",
                NeueSchichtKapazitaet = 0
            };
            var initialCount = viewModel.SchichtListe.Count;

            viewModel.SchichtHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.SchichtListe, Has.Count.EqualTo(initialCount));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Schichtkapazität muss größer als 0 sein"));
        }

        [Test]
        public void SchichtHinzufuegenCommand_DoesNotAddShift_WhenWeekdayIsMissing()
        {
            var viewModel = new MainViewModel
            {
                AktuellerBenutzer = BenutzerKontext.StandardAdmin(),
                NeueSchichtName = "Kasse Abend",
                NeueSchichtAbteilung = "Kasse",
                NeueSchichtWochentag = " ",
                NeueSchichtKapazitaet = 2
            };
            var initialCount = viewModel.SchichtListe.Count;

            viewModel.SchichtHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.SchichtListe, Has.Count.EqualTo(initialCount));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Schichtwochentag ist erforderlich"));
        }

        [Test]
        public void SchichtHinzufuegenCommand_AddsTrimmedShift_WhenInputIsValid()
        {
            var viewModel = new MainViewModel
            {
                AktuellerBenutzer = BenutzerKontext.StandardAdmin(),
                NeueSchichtName = "  Lager Spät ",
                NeueSchichtAbteilung = " Lager ",
                NeueSchichtWochentag = " Samstag ",
                NeueSchichtKapazitaet = 3
            };
            var initialCount = viewModel.SchichtListe.Count;

            viewModel.SchichtHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.SchichtListe, Has.Count.EqualTo(initialCount + 1));
            Assert.That(viewModel.SchichtListe[initialCount].Name, Is.EqualTo("Lager Spät"));
            Assert.That(viewModel.SchichtListe[initialCount].Abteilung, Is.EqualTo("Lager"));
            Assert.That(viewModel.SchichtListe[initialCount].Wochentag, Is.EqualTo("Samstag"));
            Assert.That(viewModel.SchichtListe[initialCount].BenoetigteMitarbeiter, Is.EqualTo(3));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Schicht hinzugefügt"));
        }

        [Test]
        public void FormCommands_RequeryAvailability_WhenRequiredFieldsChange()
        {
            var viewModel = new MainViewModel();
            var employeeRequeries = 0;
            var shiftRequeries = 0;
            viewModel.MitarbeiterHinzufuegenCommand.CanExecuteChanged += (sender, args) => employeeRequeries++;
            viewModel.SchichtHinzufuegenCommand.CanExecuteChanged += (sender, args) => shiftRequeries++;

            viewModel.NeuerMitarbeiterName = "Eva Retail";
            viewModel.NeueMitarbeiterAbteilung = "Kasse";
            viewModel.NeuerMitarbeiterQualifikation = "Kasse";
            viewModel.NeueSchichtName = "Kasse Abend";
            viewModel.NeueSchichtAbteilung = "Kasse";
            viewModel.NeueSchichtWochentag = "Freitag";

            Assert.That(employeeRequeries, Is.EqualTo(3));
            Assert.That(shiftRequeries, Is.EqualTo(3));
            Assert.That(viewModel.MitarbeiterHinzufuegenCommand.CanExecute(null), Is.True);
            Assert.That(viewModel.SchichtHinzufuegenCommand.CanExecute(null), Is.True);
        }

        [Test]
        public void Constructor_UsesProvidedAuthenticatedUserContext()
        {
            var benutzer = new BenutzerKontext
            {
                Benutzername = "planer@example.test",
                Rolle = Dienstplaner.Models.BenutzerRolle.Planer
            };

            var viewModel = new MainViewModel(benutzer);

            Assert.That(viewModel.AktuellerBenutzer, Is.SameAs(benutzer));
        }

        [Test]
        public void MitarbeiterHinzufuegenCommand_AllowsCreation_WithInjectedPlannerContext()
        {
            var benutzer = new BenutzerKontext
            {
                Benutzername = "planer@example.test",
                Rolle = Dienstplaner.Models.BenutzerRolle.Planer
            };
            var viewModel = new MainViewModel(benutzer)
            {
                NeuerMitarbeiterName = "Eva Retail",
                NeueMitarbeiterAbteilung = "Kasse",
                NeuerMitarbeiterQualifikation = "Kasse"
            };
            var initialCount = viewModel.MitarbeiterListe.Count;

            viewModel.MitarbeiterHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.MitarbeiterListe, Has.Count.EqualTo(initialCount + 1));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Mitarbeiter hinzugefügt"));
        }

        [Test]
        public void MitarbeiterHinzufuegenCommand_DeniesCreation_WithoutAuthorizedUserContext()
        {
            var viewModel = new MainViewModel
            {
                NeuerMitarbeiterName = "Eva Retail",
                NeueMitarbeiterAbteilung = "Kasse",
                NeuerMitarbeiterQualifikation = "Kasse"
            };
            var initialCount = viewModel.MitarbeiterListe.Count;

            viewModel.MitarbeiterHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.AktuellerBenutzer, Is.Null);
            Assert.That(viewModel.MitarbeiterListe, Has.Count.EqualTo(initialCount));
            Assert.That(viewModel.StatusNachricht, Is.EqualTo("Kein Benutzerkontext vorhanden."));
        }

    }
}
