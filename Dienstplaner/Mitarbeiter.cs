using System;
using System.Collections.Generic;
using System.Linq;

namespace Dienstplaner.Models
{
    public class Mitarbeiter
    {
        public int Id { get; set; }
        public int MandantId { get; set; }
        public int FilialeId { get; set; }
        public string Name { get; set; }
        public string Abteilung { get; set; }
        public string Qualifikation { get; set; }
        public string Filiale { get; set; }

        public int StoreId { get; set; }
        public int DepartmentId { get; set; }
        public int RoleId { get; set; }
        public List<int> SkillIds { get; set; }

        public int WochenstundenLimit { get; set; }
        public decimal SollstundenProWoche { get; set; }
        public decimal Stundenlohn { get; set; }
        public bool IstAktiv { get; set; }

        public int AktuelleWochenstunden { get; set; }
        public List<Abwesenheit> Abwesenheiten { get; set; }
        public List<Schicht> Schichten { get; set; }

        public Mitarbeiter()
        {
            SkillIds = new List<int>();
            Schichten = new List<Schicht>();
            Abwesenheiten = new List<Abwesenheit>();
            IstAktiv = true;
            WochenstundenLimit = 48;
            SollstundenProWoche = 40;
            Stundenlohn = 15;
        }

        public decimal Iststunden
        {
            get { return Schichten.Sum(x => x.NettoDauerInStunden); }
        }

        public decimal Pausenstunden
        {
            get { return Schichten.Sum(x => x.Pausenstunden); }
        }

        public decimal Zuschlagsstunden
        {
            get { return Schichten.Sum(x => x.Zuschlagsstunden); }
        }

        public decimal Ueberstunden
        {
            get { return Iststunden > SollstundenProWoche ? Iststunden - SollstundenProWoche : 0; }
        }

        public string ToAuditString()
        {
            return $"Id={Id};Name={Name};Abteilung={Abteilung};Qualifikation={Qualifikation};IstAktiv={IstAktiv};WochenstundenLimit={WochenstundenLimit};Schichten={Schichten.Count}";
        }
    }
}
