using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

namespace Dienstplaner.Auth
{
    public class AuthService
    {
        private readonly AuthorizationService _authorizationService;

        public AuthService(AuthorizationService authorizationService)
        {
            _authorizationService = authorizationService;
        }

        public ObservableCollection<UserAccount> UserAccounts { get; private set; }
            = new ObservableCollection<UserAccount>
            {
                new UserAccount
                {
                    SubjectId = "tenant-admin-1",
                    DisplayName = "Tina TenantAdmin",
                    Role = UserRole.TenantAdmin,
                    TenantId = "tenant-1",
                    StoreId = "store-1"
                },
                new UserAccount
                {
                    SubjectId = "store-manager-1",
                    DisplayName = "Sven StoreManager",
                    Role = UserRole.StoreManager,
                    TenantId = "tenant-1",
                    StoreId = "store-1"
                },
                new UserAccount
                {
                    SubjectId = "planner-1",
                    DisplayName = "Paula Planner",
                    Role = UserRole.Planner,
                    TenantId = "tenant-1",
                    StoreId = "store-1"
                },
                new UserAccount
                {
                    SubjectId = "employee-1",
                    DisplayName = "Max Mustermann",
                    Role = UserRole.Employee,
                    MitarbeiterId = 1,
                    TenantId = "tenant-1",
                    StoreId = "store-1"
                },
                new UserAccount
                {
                    SubjectId = "employee-2",
                    DisplayName = "Erika Beispiel",
                    Role = UserRole.Employee,
                    MitarbeiterId = 2,
                    TenantId = "tenant-1",
                    StoreId = "store-1"
                }
            };

        public AuthenticatedUser SignIn(UserAccount account)
        {
            if (account == null)
                return null;

            var permissions = account.Permissions != null && account.Permissions.Any()
                ? account.Permissions
                : _authorizationService.GetPermissionsForRole(account.Role);

            return new AuthenticatedUser(account, permissions);
        }
    }
}
