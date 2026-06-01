using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace Dienstplaner.Services
{
    public class DataProtectionService
    {
        public const string TransportSecurityRequirement = "TLS 1.2+ für alle externen Verbindungen";
        private static readonly byte[] Entropy = Encoding.UTF8.GetBytes("DienstplanerV2-Compliance-v1");

        public string Verschluesseln(string klartext)
        {
            if (string.IsNullOrEmpty(klartext))
                return string.Empty;

            var daten = Encoding.UTF8.GetBytes(klartext);
            var verschluesselt = ProtectedData.Protect(daten, Entropy, DataProtectionScope.CurrentUser);
            return Convert.ToBase64String(verschluesselt);
        }

        public string Entschluesseln(string geheimtext)
        {
            if (string.IsNullOrEmpty(geheimtext))
                return string.Empty;

            var daten = Convert.FromBase64String(geheimtext);
            var klartext = ProtectedData.Unprotect(daten, Entropy, DataProtectionScope.CurrentUser);
            return Encoding.UTF8.GetString(klartext);
        }

        public void SchreibeVerschluesselteDatei(string pfad, string inhalt)
        {
            var verzeichnis = Path.GetDirectoryName(pfad);
            if (!string.IsNullOrEmpty(verzeichnis))
                Directory.CreateDirectory(verzeichnis);

            File.WriteAllText(pfad, Verschluesseln(inhalt), Encoding.UTF8);
        }
    }
}
