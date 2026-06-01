using System.Collections.Generic;
using System.Linq;

namespace Dienstplaner.Auth
{
    public class AuthenticatedUser
    {
        public string SubjectId { get; private set; }
        public string DisplayName { get; private set; }
        public UserRole Role { get; private set; }
        public int? MitarbeiterId { get; private set; }
        public string TenantId { get; private set; }
        public string StoreId { get; private set; }
        public IReadOnlyCollection<Permission> Permissions { get; private set; }

        public AuthenticatedUser(UserAccount account, IEnumerable<Permission> permissions)
        {
            SubjectId = account.SubjectId;
            DisplayName = account.DisplayName;
            Role = account.Role;
            MitarbeiterId = account.MitarbeiterId;
            TenantId = account.TenantId;
            StoreId = account.StoreId;
            Permissions = permissions.ToList().AsReadOnly();
        }

        public bool HasPermission(Permission permission)
        {
            return Permissions.Contains(permission);
        }
    }
}
