using System;
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
        public void MainViewModel_ExposesAllPropertiesBoundByMainWindow()
        {
            var viewModel = new MainViewModel();

            Assert.Multiple(() =>
            {
                Assert.That(viewModel.SchichtLoeschenCommand, Is.Not.Null);
                Assert.That(viewModel.DienstplanVeroeffentlichenCommand, Is.Not.Null);
                Assert.That(viewModel.DsgvoAuskunftCommand, Is.Not.Null);
                Assert.That(viewModel.DsgvoLoeschenCommand, Is.Not.Null);
                Assert.That(viewModel.AuditLog, Is.Not.Null);
                Assert.That(viewModel.ZuweisungsFehler, Is.Not.Null);
                Assert.That(viewModel.ZuweisungsWarnungen, Is.Not.Null);
            });
        }

        [Test]
        public void ZuweisenCommand_ShowsAssignmentFailureInBoundErrorCollection()
        {
            var viewModel = new MainViewModel
            {
                AusgewaehlterMitarbeiter = null,
                AusgewaehlteSchicht = null
            };

            viewModel.ZuweisenCommand.Execute(null);

            Assert.That(viewModel.ZuweisungsFehler, Is.EqualTo(new[] { "Ungültige Auswahl" }));
            Assert.That(viewModel.ZuweisungsWarnungen, Is.Empty);
        }

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

        [Test]
        public void HinzufuegenCommands_AreClickable_BeforeRequiredFieldsAreFilled()
        {
            var viewModel = new MainViewModel();

            Assert.That(viewModel.MitarbeiterHinzufuegenCommand.CanExecute(null), Is.True);
            Assert.That(viewModel.SchichtHinzufuegenCommand.CanExecute(null), Is.True);
        }

        [Test]
        public void SchichtHinzufuegenCommand_UsesEnteredDateAndTimes()
        {
            var viewModel = new MainViewModel
            {
                NeueSchichtName = "Inventur",
                NeueSchichtAbteilung = "Lager",
                NeueSchichtWochentag = "Mittwoch",
                NeueSchichtDatum = new DateTime(2026, 6, 10),
                NeueSchichtStartzeit = "09:15",
                NeueSchichtEndzeit = "17:45",
                NeueSchichtKapazitaet = 4,
                NeueSchichtPausenstunden = 0.75m
            };
            var initialCount = viewModel.SchichtListe.Count;

            viewModel.SchichtHinzufuegenCommand.Execute(null);

            var schicht = viewModel.SchichtListe[initialCount];
            Assert.That(schicht.Start, Is.EqualTo(new DateTime(2026, 6, 10, 9, 15, 0)));
            Assert.That(schicht.Ende, Is.EqualTo(new DateTime(2026, 6, 10, 17, 45, 0)));
            Assert.That(schicht.Pausenstunden, Is.EqualTo(0.75m));
        }

        [Test]
        public void SchichtHinzufuegenCommand_DoesNotAddShift_WhenEndTimeIsBeforeStartTime()
        {
            var viewModel = new MainViewModel
            {
                NeueSchichtName = "Inventur",
                NeueSchichtAbteilung = "Lager",
                NeueSchichtWochentag = "Mittwoch",
                NeueSchichtStartzeit = "17:00",
                NeueSchichtEndzeit = "09:00",
                NeueSchichtKapazitaet = 2
            };
            var initialCount = viewModel.SchichtListe.Count;

            viewModel.SchichtHinzufuegenCommand.Execute(null);

            Assert.That(viewModel.SchichtListe, Has.Count.EqualTo(initialCount));
            Assert.That(viewModel.StatusNachricht, Does.Contain("Endzeit muss nach der Startzeit liegen"));
        }
    }
}
