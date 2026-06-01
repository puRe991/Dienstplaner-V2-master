using System.Threading;
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
    }
}
