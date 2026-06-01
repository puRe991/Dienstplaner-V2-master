namespace Dienstplaner.Infrastructure.Migrations
{
    public class SqlMigration
    {
        public SqlMigration(string id, string script)
        {
            Id = id;
            Script = script;
        }

        public string Id { get; private set; }
        public string Script { get; private set; }
    }
}
