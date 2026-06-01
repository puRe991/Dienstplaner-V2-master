using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace Dienstplaner.Auth
{
    public class JwtAuthenticationService
    {
        private readonly AuthorizationService _authorizationService;
        private readonly JwtValidationOptions _options;

        public JwtAuthenticationService(AuthorizationService authorizationService, JwtValidationOptions options)
        {
            _authorizationService = authorizationService;
            _options = options;
        }

        public AuthenticatedUser AuthenticateBearerToken(string authorizationHeader)
        {
            if (string.IsNullOrWhiteSpace(authorizationHeader) || !authorizationHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
                return null;

            var token = authorizationHeader.Substring("Bearer ".Length).Trim();
            var claims = ReadJwtPayload(token);
            if (claims == null)
                return null;

            if (!ValidateRegisteredClaims(claims))
                return null;

            UserRole role;
            if (!TryReadRole(claims, out role))
                return null;

            var account = new UserAccount
            {
                SubjectId = GetClaim(claims, "sub"),
                DisplayName = GetClaim(claims, "name") ?? GetClaim(claims, "preferred_username") ?? GetClaim(claims, "email"),
                Role = role,
                TenantId = GetClaim(claims, _options.TenantClaimName),
                StoreId = GetClaim(claims, _options.StoreClaimName),
                MitarbeiterId = ReadNullableIntClaim(claims, _options.EmployeeClaimName)
            };

            return new AuthenticatedUser(account, _authorizationService.GetPermissionsForRole(role));
        }

        private bool ValidateRegisteredClaims(Dictionary<string, string> claims)
        {
            var issuer = GetClaim(claims, "iss");
            if (!string.IsNullOrWhiteSpace(_options.RequiredIssuer) && issuer != _options.RequiredIssuer)
                return false;

            var audience = GetClaim(claims, "aud");
            if (!string.IsNullOrWhiteSpace(_options.Audience) && audience != _options.Audience)
                return false;

            var expiresAt = ReadNullableLongClaim(claims, "exp");
            if (expiresAt.HasValue)
            {
                var validUntil = DateTimeOffset.FromUnixTimeSeconds(expiresAt.Value);
                if (validUntil <= DateTimeOffset.UtcNow)
                    return false;
            }

            return true;
        }

        private bool TryReadRole(Dictionary<string, string> claims, out UserRole role)
        {
            var roleValue = GetClaim(claims, "role") ?? GetClaim(claims, "roles");
            return Enum.TryParse(roleValue, true, out role);
        }

        private static Dictionary<string, string> ReadJwtPayload(string token)
        {
            var segments = token.Split('.');
            if (segments.Length < 2)
                return null;

            var json = Encoding.UTF8.GetString(Base64UrlDecode(segments[1]));
            return ReadFlatJsonClaims(json);
        }

        private static Dictionary<string, string> ReadFlatJsonClaims(string json)
        {
            var claims = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var matches = Regex.Matches(json, "\\\"(?<key>[^\\\"]+)\\\"\\s*:\\s*(?<value>\\\"([^\\\"]*)\\\"|-?\\d+|true|false|null|\\[[^\\]]*\\])");
            foreach (Match match in matches)
            {
                var value = match.Groups["value"].Value.Trim();
                if (value.StartsWith("[", StringComparison.Ordinal))
                    value = Regex.Match(value, "\\\"(?<item>[^\\\"]+)\\\"").Groups["item"].Value;
                else if (value.StartsWith("\"", StringComparison.Ordinal) && value.EndsWith("\"", StringComparison.Ordinal))
                    value = value.Substring(1, value.Length - 2);

                claims[match.Groups["key"].Value] = value;
            }

            return claims;
        }

        private static byte[] Base64UrlDecode(string input)
        {
            var output = input.Replace('-', '+').Replace('_', '/');
            switch (output.Length % 4)
            {
                case 2:
                    output += "==";
                    break;
                case 3:
                    output += "=";
                    break;
            }

            return Convert.FromBase64String(output);
        }

        private static string GetClaim(Dictionary<string, string> claims, string name)
        {
            if (string.IsNullOrWhiteSpace(name))
                return null;

            string value;
            return claims.TryGetValue(name, out value) ? value : null;
        }

        private static int? ReadNullableIntClaim(Dictionary<string, string> claims, string name)
        {
            var value = GetClaim(claims, name);
            int result;
            return int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out result) ? result : (int?)null;
        }

        private static long? ReadNullableLongClaim(Dictionary<string, string> claims, string name)
        {
            var value = GetClaim(claims, name);
            long result;
            return long.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out result) ? result : (long?)null;
        }
    }
}
