using System.Data;

namespace Dienstplaner.Infrastructure
{
    public interface IDatabaseConnectionFactory
    {
        IDbConnection CreateConnection();
    }
}
