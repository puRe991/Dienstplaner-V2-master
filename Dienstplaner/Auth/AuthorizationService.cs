using System.Collections.Generic;
using System.Linq;
using Dienstplaner.Models;

namespace Dienstplaner.Auth
{
    public class AuthorizationService
    {
        private static readonly Dictionary<UserRole, Permission[]> RolePermissions =
            new Dictionary<UserRole, Permission[]>
            {
                {
                    UserRole.TenantAdmin,
                    new[]
                    {
                        Permission.ViewEmployeeData,
                        Permission.EditEmployeeData,
                        Permission.ViewOwnEmployeeData,
                        Permission.ViewSchedule,
                        Permission.EditSchedule,
                        Permission.ViewOwnSchedule,
                        Permission.ApproveSchedule,
                        Permission.ExportSchedule,
                        Permission.ManageAdminFunctions,
                        Permission.ViewOwnRequests,
                        Permission.ManageRequests
                    }
                },
                {
                    UserRole.StoreManager,
                    new[]
                    {
                        Permission.ViewEmployeeData,
                        Permission.EditEmployeeData,
                        Permission.ViewOwnEmployeeData,
                        Permission.ViewSchedule,
                        Permission.EditSchedule,
                        Permission.ViewOwnSchedule,
                        Permission.ApproveSchedule,
                        Permission.ExportSchedule,
                        Permission.ViewOwnRequests,
                        Permission.ManageRequests
                    }
                },
                {
                    UserRole.Planner,
                    new[]
                    {
                        Permission.ViewEmployeeData,
                        Permission.ViewOwnEmployeeData,
                        Permission.ViewSchedule,
                        Permission.EditSchedule,
                        Permission.ViewOwnSchedule,
                        Permission.ExportSchedule,
                        Permission.ViewOwnRequests,
                        Permission.ManageRequests
                    }
                },
                {
                    UserRole.Employee,
                    new[]
                    {
                        Permission.ViewOwnEmployeeData,
                        Permission.ViewOwnSchedule,
                        Permission.ViewOwnRequests
                    }
                }
            };

        public IReadOnlyCollection<Permission> GetPermissionsForRole(UserRole role)
        {
            return RolePermissions[role].ToList().AsReadOnly();
        }

        public bool HasPermission(AuthenticatedUser user, Permission permission)
        {
            return user != null && user.HasPermission(permission);
        }

        public bool CanViewEmployee(AuthenticatedUser user, Mitarbeiter mitarbeiter)
        {
            if (user == null || mitarbeiter == null)
                return false;

            if (HasPermission(user, Permission.ViewEmployeeData))
                return true;

            return HasPermission(user, Permission.ViewOwnEmployeeData) &&
                user.MitarbeiterId.HasValue &&
                mitarbeiter.Id == user.MitarbeiterId.Value;
        }

        public bool CanViewShift(AuthenticatedUser user, Schicht schicht)
        {
            if (user == null || schicht == null)
                return false;

            if (HasPermission(user, Permission.ViewSchedule))
                return true;

            return HasPermission(user, Permission.ViewOwnSchedule) &&
                user.MitarbeiterId.HasValue &&
                schicht.MitarbeiterIds.Contains(user.MitarbeiterId.Value);
        }

        public bool CanViewRequest(AuthenticatedUser user, MitarbeiterAnfrage anfrage)
        {
            if (user == null || anfrage == null)
                return false;

            if (HasPermission(user, Permission.ManageRequests))
                return true;

            return HasPermission(user, Permission.ViewOwnRequests) &&
                user.MitarbeiterId.HasValue &&
                anfrage.MitarbeiterId == user.MitarbeiterId.Value;
        }

        public bool CanEditSchedule(AuthenticatedUser user)
        {
            return HasPermission(user, Permission.EditSchedule);
        }

        public bool CanEditEmployeeData(AuthenticatedUser user)
        {
            return HasPermission(user, Permission.EditEmployeeData);
        }
    }
}
