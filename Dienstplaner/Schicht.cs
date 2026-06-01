using System;
using System.Collections.Generic;
using System.Globalization;

namespace Dienstplaner.Models
{
    public class Schicht
    {
        public int Id { get; set; }
        public string Name { get; set; }

        public int StoreId { get; set; }
        public int DepartmentId { get; set; }
        public int RoleId { get; set; }

        public DateTime StartUtc { get; set; }
        public DateTime EndUtc { get; set; }
        public TimeSpan BreakDuration { get; set; }

        public List<int> RequiredSkillIds { get; set; }
        public int RequiredHeadcount { get; set; }
        public string CostCenter { get; set; }

        public List<Besetzungsfenster> Besetzungsfenster { get; set; }
        public List<string> MitarbeiterNamen { get; set; }

        public SchichtVorlage Vorlage { get; set; }

        public Schicht()
        {
            RequiredSkillIds = new List<int>();
            Besetzungsfenster = new List<Besetzungsfenster>();
            MitarbeiterNamen = new List<string>();
        }

        public string Abteilung
        {
            get { return DepartmentId > 0 ? DepartmentId.ToString(CultureInfo.InvariantCulture) : string.Empty; }
            set
            {
                int parsed;
                DepartmentId = int.TryParse(value, out parsed) ? parsed : 0;
            }
        }

        public string Wochentag
        {
            get { return StartUtc == default(DateTime) ? string.Empty : StartUtc.ToLocalTime().ToString("dddd", CultureInfo.CurrentCulture); }
        }

        public DateTime Start
        {
            get { return StartUtc == default(DateTime) ? default(DateTime) : StartUtc.ToLocalTime(); }
            set { StartUtc = DateTime.SpecifyKind(value, DateTimeKind.Local).ToUniversalTime(); }
        }

        public DateTime Ende
        {
            get { return EndUtc == default(DateTime) ? default(DateTime) : EndUtc.ToLocalTime(); }
            set { EndUtc = DateTime.SpecifyKind(value, DateTimeKind.Local).ToUniversalTime(); }
        }

        public int BenoetigteMitarbeiter
        {
            get { return RequiredHeadcount; }
            set { RequiredHeadcount = value; }
        }

        public string BenoetigteQualifikation { get; set; }

        public bool IstVoll
        {
            get { return MitarbeiterNamen.Count >= RequiredHeadcount; }
        }

        public int DauerInStunden
        {
            get { return (int)(EndUtc - StartUtc - BreakDuration).TotalHours; }
        }

        public string ZeitraumAnzeige
        {
            get
            {
                if (StartUtc == default(DateTime) || EndUtc == default(DateTime))
                    return string.Empty;

                return string.Format(CultureInfo.CurrentCulture, "{0:g} - {1:t}", StartUtc.ToLocalTime(), EndUtc.ToLocalTime());
            }
        }

        public string BesetzungAnzeige
        {
            get { return string.Format(CultureInfo.CurrentCulture, "Ist {0} / Soll {1}", MitarbeiterNamen.Count, RequiredHeadcount); }
        }
    }

    public class SchichtVorlage
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public int StoreId { get; set; }
        public int DepartmentId { get; set; }
        public int RoleId { get; set; }
        public DayOfWeek Wochentag { get; set; }
        public TimeSpan Startzeit { get; set; }
        public TimeSpan Endzeit { get; set; }
        public TimeSpan BreakDuration { get; set; }
        public List<int> RequiredSkillIds { get; set; }
        public int RequiredHeadcount { get; set; }
        public string CostCenter { get; set; }
        public Wiederholungsregel Wiederholung { get; set; }
        public List<Besetzungsfenster> Besetzungsfenster { get; set; }

        public SchichtVorlage()
        {
            RequiredSkillIds = new List<int>();
            Wiederholung = new Wiederholungsregel();
            Besetzungsfenster = new List<Besetzungsfenster>();
        }

        public Schicht ErzeugeSchicht(DateTime datum, int id)
        {
            DateTime startLocal = datum.Date.Add(Startzeit);
            DateTime endLocal = datum.Date.Add(Endzeit);

            if (endLocal <= startLocal)
                endLocal = endLocal.AddDays(1);

            return new Schicht
            {
                Id = id,
                Name = Name,
                StoreId = StoreId,
                DepartmentId = DepartmentId,
                RoleId = RoleId,
                Start = startLocal,
                Ende = endLocal,
                BreakDuration = BreakDuration,
                RequiredSkillIds = new List<int>(RequiredSkillIds),
                RequiredHeadcount = RequiredHeadcount,
                CostCenter = CostCenter,
                Vorlage = this,
                Besetzungsfenster = KopiereBesetzungsfenster(Besetzungsfenster)
            };
        }

        private static List<Besetzungsfenster> KopiereBesetzungsfenster(IEnumerable<Besetzungsfenster> fenster)
        {
            var kopie = new List<Besetzungsfenster>();
            foreach (var eintrag in fenster)
            {
                kopie.Add(new Besetzungsfenster
                {
                    Von = eintrag.Von,
                    Bis = eintrag.Bis,
                    Mindestbesetzung = eintrag.Mindestbesetzung,
                    Sollbesetzung = eintrag.Sollbesetzung,
                    Maximalbesetzung = eintrag.Maximalbesetzung
                });
            }

            return kopie;
        }
    }

    public class Wiederholungsregel
    {
        public Wiederholungsart Art { get; set; }
        public int IntervallInWochen { get; set; }
        public DateTime GueltigAb { get; set; }
        public DateTime? GueltigBis { get; set; }

        public Wiederholungsregel()
        {
            Art = Wiederholungsart.Woechentlich;
            IntervallInWochen = 1;
            GueltigAb = DateTime.Today;
        }
    }

    public enum Wiederholungsart
    {
        Keine,
        Woechentlich,
        Zweiwoechentlich
    }

    public class Besetzungsfenster
    {
        public TimeSpan Von { get; set; }
        public TimeSpan Bis { get; set; }
        public int Mindestbesetzung { get; set; }
        public int Sollbesetzung { get; set; }
        public int Maximalbesetzung { get; set; }

        public string Anzeige
        {
            get
            {
                return string.Format(CultureInfo.CurrentCulture, "{0:hh\\:mm}-{1:hh\\:mm}: Min {2}, Soll {3}, Max {4}", Von, Bis, Mindestbesetzung, Sollbesetzung, Maximalbesetzung);
            }
        }
    }


    public class Wochenplan
    {
        public int Id { get; set; }
        public int StoreId { get; set; }
        public DateTime Wochenbeginn { get; set; }
        public List<SchichtVorlage> Vorlagen { get; set; }
        public List<Schicht> Schichten { get; set; }

        public Wochenplan()
        {
            Vorlagen = new List<SchichtVorlage>();
            Schichten = new List<Schicht>();
        }

        public void GeneriereSchichtenAusVorlagen()
        {
            Schichten.Clear();
            int nextId = 1;

            foreach (var vorlage in Vorlagen)
            {
                if (StoreId > 0 && vorlage.StoreId != StoreId)
                    continue;

                DateTime datum = Wochenbeginn.Date.AddDays(((int)vorlage.Wochentag - (int)Wochenbeginn.DayOfWeek + 7) % 7);

                if (!IstVorlageInWocheGueltig(vorlage, datum))
                    continue;

                Schichten.Add(vorlage.ErzeugeSchicht(datum, nextId++));
            }
        }

        private static bool IstVorlageInWocheGueltig(SchichtVorlage vorlage, DateTime datum)
        {
            if (vorlage.Wiederholung.Art == Wiederholungsart.Keine)
                return datum.Date == vorlage.Wiederholung.GueltigAb.Date;

            if (datum.Date < vorlage.Wiederholung.GueltigAb.Date)
                return false;

            if (vorlage.Wiederholung.GueltigBis.HasValue && datum.Date > vorlage.Wiederholung.GueltigBis.Value.Date)
                return false;

            int intervall = vorlage.Wiederholung.Art == Wiederholungsart.Zweiwoechentlich
                ? 2
                : Math.Max(1, vorlage.Wiederholung.IntervallInWochen);
            int wochenSeitStart = (int)((datum.Date - vorlage.Wiederholung.GueltigAb.Date).TotalDays / 7);

            return wochenSeitStart % intervall == 0;
        }
    }

    public class Oeffnungszeiten
    {
        public int StoreId { get; set; }
        public DayOfWeek Wochentag { get; set; }
        public TimeSpan OeffnetUm { get; set; }
        public TimeSpan SchliesstUm { get; set; }
        public bool IstGeschlossen { get; set; }
    }

    public class Sonderoeffnung
    {
        public int StoreId { get; set; }
        public DateTime Datum { get; set; }
        public TimeSpan OeffnetUm { get; set; }
        public TimeSpan SchliesstUm { get; set; }
        public string Grund { get; set; }
    }

    public class Feiertag
    {
        public DateTime Datum { get; set; }
        public string Name { get; set; }
        public string Bundesland { get; set; }
        public bool Arbeitsfrei { get; set; }
    }

    public class VerkaufsoffenerSonntag
    {
        public int StoreId { get; set; }
        public DateTime Datum { get; set; }
        public TimeSpan OeffnetUm { get; set; }
        public TimeSpan SchliesstUm { get; set; }
        public string Anlass { get; set; }
    }

    public class Filialkalender
    {
        public int StoreId { get; set; }
        public List<Oeffnungszeiten> RegelOeffnungszeiten { get; set; }
        public List<Sonderoeffnung> Sonderoeffnungen { get; set; }
        public List<Feiertag> Feiertage { get; set; }
        public List<VerkaufsoffenerSonntag> VerkaufsoffeneSonntage { get; set; }

        public Filialkalender()
        {
            RegelOeffnungszeiten = new List<Oeffnungszeiten>();
            Sonderoeffnungen = new List<Sonderoeffnung>();
            Feiertage = new List<Feiertag>();
            VerkaufsoffeneSonntage = new List<VerkaufsoffenerSonntag>();
        }

        public bool IstGeoeffnet(DateTime datum, out TimeSpan oeffnetUm, out TimeSpan schliesstUm)
        {
            var sonderoeffnung = Sonderoeffnungen.Find(x => x.StoreId == StoreId && x.Datum.Date == datum.Date);
            if (sonderoeffnung != null)
            {
                oeffnetUm = sonderoeffnung.OeffnetUm;
                schliesstUm = sonderoeffnung.SchliesstUm;
                return true;
            }

            var verkaufsoffenerSonntag = VerkaufsoffeneSonntage.Find(x => x.StoreId == StoreId && x.Datum.Date == datum.Date);
            if (verkaufsoffenerSonntag != null)
            {
                oeffnetUm = verkaufsoffenerSonntag.OeffnetUm;
                schliesstUm = verkaufsoffenerSonntag.SchliesstUm;
                return true;
            }

            var feiertag = Feiertage.Find(x => x.Datum.Date == datum.Date && x.Arbeitsfrei);
            if (feiertag != null)
            {
                oeffnetUm = TimeSpan.Zero;
                schliesstUm = TimeSpan.Zero;
                return false;
            }

            var regel = RegelOeffnungszeiten.Find(x => x.StoreId == StoreId && x.Wochentag == datum.DayOfWeek);
            if (regel == null || regel.IstGeschlossen)
            {
                oeffnetUm = TimeSpan.Zero;
                schliesstUm = TimeSpan.Zero;
                return false;
            }

            oeffnetUm = regel.OeffnetUm;
            schliesstUm = regel.SchliesstUm;
            return true;
        }
    }

}
