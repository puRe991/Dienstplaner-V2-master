namespace Dienstplaner.Auth
{
    public class JwtValidationOptions
    {
        public string Authority { get; set; }
        public string Audience { get; set; }
        public string RequiredIssuer { get; set; }
        public string TenantClaimName { get; set; } = "tenant_id";
        public string StoreClaimName { get; set; } = "store_id";
        public string EmployeeClaimName { get; set; } = "employee_id";
    }
}
