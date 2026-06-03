using System;
using System.Collections.Generic;

namespace Dienstplaner.Models
{
    public class BenutzerKontext
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Email { get; set; }
        public BenutzerRolle Rolle { get; set; }
    }

    public enum BenutzerRolle
    {
        Personalwesen,
        Filialleiter,
        Planer
    }
}
