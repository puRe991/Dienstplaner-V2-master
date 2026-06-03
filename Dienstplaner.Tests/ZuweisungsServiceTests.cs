using System;
using Dienstplaner.Models;
using Dienstplaner.Services;
using Dienstplaner.Tests.TestData;
using NUnit.Framework;

namespace Dienstplaner.Tests
{
    [TestFixture]
    public class ZuweisungsServiceTests
    {
        private ZuweisungsService _service;

        [SetUp]
        public void SetUp()
        {
            _service = new ZuweisungsService();
        }

        [Test]
        public void Zuweisen_ReturnsInvalidSelection_WhenMitarbeiterIsMissing()
        {
            var result = _service.Zuweisen(null, RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Ungültige Auswahl"));
        }

        [Test]
        public void Zuweisen_ReturnsConflict_WhenEmployeeAlreadyHasOverlappingShift()
        {
            var mitarbeiter = RetailTestDataFactory.KassiererVollzeit();
            mitarbeiter.Schichten.Add(new Schicht
            {
                Name = "Bestehende Kasse",
                Start = new DateTime(2026, 6, 1, 7, 0, 0),
                Ende = new DateTime(2026, 6, 1, 12, 0, 0),
                BenoetigteMitarbeiter = 1
            });

            var result = _service.Zuweisen(mitarbeiter, RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Zeitkonflikt"));
        }

        [Test]
        public void Zuweisen_AllowsAdjacentShiftsWithoutConflict()
        {
            var mitarbeiter = RetailTestDataFactory.KassiererVollzeit();
            mitarbeiter.Schichten.Add(new Schicht
            {
                Name = "Vorherige Kasse",
                Start = new DateTime(2026, 6, 1, 6, 0, 0),
                Ende = new DateTime(2026, 6, 1, 8, 0, 0),
                BenoetigteMitarbeiter = 1
            });

            var result = _service.Zuweisen(mitarbeiter, RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Zuweisung erfolgreich"));
            Assert.That(mitarbeiter.Schichten, Has.Count.EqualTo(2));
        }

        [Test]
        public void Zuweisen_ReturnsCapacityError_WhenShiftIsFull()
        {
            var schicht = RetailTestDataFactory.KassenFruehschicht(benoetigteMitarbeiter: 1);
            schicht.MitarbeiterNamen.Add("Bereits Besetzt");

            var result = _service.Zuweisen(RetailTestDataFactory.KassiererVollzeit(), schicht);

            Assert.That(result, Is.EqualTo("Schicht ist bereits voll"));
        }

        [Test]
        public void Zuweisen_ReturnsQualificationError_WhenEmployeeQualificationDoesNotMatchShift()
        {
            var result = _service.Zuweisen(
                RetailTestDataFactory.LagerMitarbeiter(),
                RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Qualifikation passt nicht"));
        }

        [Test]
        public void Zuweisen_ReturnsAvailabilityError_WhenEmployeeIsSickOrInactive()
        {
            var result = _service.Zuweisen(
                RetailTestDataFactory.KrankGemeldeterKassierer(),
                RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Mitarbeiter ist nicht verfügbar"));
        }

        [Test]
        public void Zuweisen_ReturnsWeeklyLimitError_WhenAssignedShiftsWouldExceedLimit()
        {
            var mitarbeiter = RetailTestDataFactory.TeilzeitKassierer(aktuelleWochenstunden: 0);
            mitarbeiter.Schichten.Add(new Schicht
            {
                Name = "Bestehende lange Schicht",
                Start = new DateTime(2026, 6, 2, 0, 0, 0),
                Ende = new DateTime(2026, 6, 2, 15, 0, 0),
                BenoetigteMitarbeiter = 1
            });

            var result = _service.Zuweisen(mitarbeiter, RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Wochenstundenlimit überschritten"));
        }

        [Test]
        public void Zuweisen_IgnoresStaleWeeklyHoursCounter_WhenNoShiftsAreAssigned()
        {
            var mitarbeiter = RetailTestDataFactory.TeilzeitKassierer(aktuelleWochenstunden: 20);

            var result = _service.Zuweisen(mitarbeiter, RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Zuweisung erfolgreich"));
            Assert.That(mitarbeiter.AktuelleWochenstunden, Is.EqualTo(6));
        }

        [Test]
        public void Zuweisen_IgnoresAssignedHours_FromAnotherWeek()
        {
            var mitarbeiter = RetailTestDataFactory.TeilzeitKassierer(aktuelleWochenstunden: 20);
            mitarbeiter.Schichten.Add(new Schicht
            {
                Name = "Schicht aus Vorwoche",
                Start = new DateTime(2026, 5, 25, 8, 0, 0),
                Ende = new DateTime(2026, 5, 25, 22, 0, 0),
                BenoetigteMitarbeiter = 1
            });

            var result = _service.Zuweisen(mitarbeiter, RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Zuweisung erfolgreich"));
            Assert.That(mitarbeiter.AktuelleWochenstunden, Is.EqualTo(6));
        }

        [Test]
        public void Zuweisen_IncludesFractionalAssignedHours_InWeeklyLimitCheck()
        {
            var mitarbeiter = RetailTestDataFactory.TeilzeitKassierer(aktuelleWochenstunden: 4);
            mitarbeiter.WochenstundenLimit = 10;
            mitarbeiter.Schichten.Add(new Schicht
            {
                Name = "Bestehende kurze Schicht",
                Start = new DateTime(2026, 6, 2, 8, 0, 0),
                Ende = new DateTime(2026, 6, 2, 13, 0, 0),
                Pausenstunden = 0.5m,
                BenoetigteMitarbeiter = 1
            });

            var result = _service.Zuweisen(mitarbeiter, RetailTestDataFactory.KassenFruehschicht());

            Assert.That(result, Is.EqualTo("Wochenstundenlimit überschritten"));
        }

        [Test]
        public void Zuweisen_AddsEmployeeToWeekendRetailShift_WhenRulesPass()
        {
            var mitarbeiter = RetailTestDataFactory.KassiererVollzeit();
            var schicht = RetailTestDataFactory.WochenendeKasse();

            var result = _service.Zuweisen(mitarbeiter, schicht);

            Assert.That(result, Is.EqualTo("Zuweisung erfolgreich"));
            Assert.That(schicht.MitarbeiterNamen, Does.Contain(mitarbeiter.Name));
            Assert.That(mitarbeiter.AktuelleWochenstunden, Is.EqualTo(8));
        }

        [Test]
        public void Zuweisen_AddsEmployeeToHolidayRetailShift_WhenRulesPass()
        {
            var mitarbeiter = RetailTestDataFactory.KassiererVollzeit();
            var schicht = RetailTestDataFactory.FeiertagKasse();

            var result = _service.Zuweisen(mitarbeiter, schicht);

            Assert.That(result, Is.EqualTo("Zuweisung erfolgreich"));
            Assert.That(schicht.Wochentag, Is.EqualTo("Feiertag"));
            Assert.That(schicht.MitarbeiterNamen, Does.Contain(mitarbeiter.Name));
        }
    }
}
