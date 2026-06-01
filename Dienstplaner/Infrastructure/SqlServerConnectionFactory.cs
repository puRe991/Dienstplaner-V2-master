using System.Configuration;
using System.Data;
using System.Data.SqlClient;

namespace Dienstplaner.Infrastructure
{
    public class SqlServerConnectionFactory : IDatabaseConnectionFactory
    {
        private readonly string _connectionString;

        public SqlServerConnectionFactory(string connectionStringName = "DienstplanerDb")
        {
            ConnectionStringSettings settings = ConfigurationManager.ConnectionStrings[connectionStringName];
            _connectionString = settings != null
                ? settings.ConnectionString
                : @"Data Source=(localdb)\MSSQLLocalDB;Initial Catalog=Dienstplaner;Integrated Security=True;MultipleActiveResultSets=True";
        }

        public IDbConnection CreateConnection()
        {
            return new SqlConnection(_connectionString);
        }
    }
}
