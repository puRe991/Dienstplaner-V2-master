using System.Collections.Generic;

namespace Dienstplaner.Auth
{
    public class EndpointAuthorizationService
    {
        private readonly JwtAuthenticationService _jwtAuthenticationService;
        private readonly AuthorizationService _authorizationService;
        private readonly Dictionary<string, Permission> _endpointPermissions;

        public EndpointAuthorizationService(JwtAuthenticationService jwtAuthenticationService, AuthorizationService authorizationService)
        {
            _jwtAuthenticationService = jwtAuthenticationService;
            _authorizationService = authorizationService;
            _endpointPermissions = new Dictionary<string, Permission>
            {
                { "GET /api/employees", Permission.ViewEmployeeData },
                { "POST /api/employees", Permission.EditEmployeeData },
                { "GET /api/schedule", Permission.ViewSchedule },
                { "PUT /api/schedule", Permission.EditSchedule },
                { "POST /api/approvals", Permission.ApproveSchedule },
                { "GET /api/exports", Permission.ExportSchedule },
                { "POST /api/admin", Permission.ManageAdminFunctions },
                { "GET /api/requests", Permission.ManageRequests }
            };
        }

        public bool IsAuthorized(string httpMethod, string route, string authorizationHeader, int? resourceOwnerMitarbeiterId)
        {
            var user = _jwtAuthenticationService.AuthenticateBearerToken(authorizationHeader);
            if (user == null)
                return false;

            var key = string.Format("{0} {1}", httpMethod, route);
            Permission permission;
            if (_endpointPermissions.TryGetValue(key, out permission))
                return _authorizationService.HasPermission(user, permission);

            if (route == "/api/me" || route == "/api/my-shifts" || route == "/api/my-requests")
                return user.MitarbeiterId.HasValue && user.MitarbeiterId == resourceOwnerMitarbeiterId;

            return false;
        }
    }
}
