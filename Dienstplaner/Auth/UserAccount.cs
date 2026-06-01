using System.Collections.Generic;

namespace Dienstplaner.Auth
{
    public class UserAccount
    {
        public string SubjectId { get; set; }
        public string DisplayName { get; set; }
        public UserRole Role { get; set; }
        public int? MitarbeiterId { get; set; }
        public string TenantId { get; set; }
        public string StoreId { get; set; }

        public List<Permission> Permissions { get; set; }

        public UserAccount()
        {
            Permissions = new List<Permission>();
        }

        public string AnzeigeName
        {
            get { return string.Format("{0} ({1})", DisplayName, Role); }
        }
    }
}
