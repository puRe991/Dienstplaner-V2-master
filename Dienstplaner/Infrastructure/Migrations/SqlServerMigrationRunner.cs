using System;
using System.Collections.Generic;
using System.Data;

namespace Dienstplaner.Infrastructure.Migrations
{
    public class SqlServerMigrationRunner
    {
        private readonly IDatabaseConnectionFactory _connectionFactory;

        public SqlServerMigrationRunner(IDatabaseConnectionFactory connectionFactory)
        {
            _connectionFactory = connectionFactory;
        }

        public void Migrate()
        {
            using (IDbConnection connection = _connectionFactory.CreateConnection())
            {
                connection.Open();
                Execute(connection, null, @"
IF OBJECT_ID(N'dbo.SchemaMigrations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.SchemaMigrations(
        Id NVARCHAR(128) NOT NULL CONSTRAINT PK_SchemaMigrations PRIMARY KEY,
        AppliedAt DATETIME2 NOT NULL CONSTRAINT DF_SchemaMigrations_AppliedAt DEFAULT SYSUTCDATETIME()
    );
END");

                foreach (SqlMigration migration in Migrations)
                {
                    if (HasMigration(connection, migration.Id))
                        continue;

                    using (IDbTransaction transaction = connection.BeginTransaction())
                    {
                        Execute(connection, transaction, migration.Script);
                        Execute(connection, transaction,
                            "INSERT INTO dbo.SchemaMigrations(Id) VALUES (@Id)",
                            new Dictionary<string, object> { { "@Id", migration.Id } });
                        transaction.Commit();
                    }
                }
            }
        }

        private bool HasMigration(IDbConnection connection, string id)
        {
            using (IDbCommand command = connection.CreateCommand())
            {
                command.CommandText = "SELECT COUNT(1) FROM dbo.SchemaMigrations WHERE Id = @Id";
                AddParameter(command, "@Id", id);
                return Convert.ToInt32(command.ExecuteScalar()) > 0;
            }
        }

        private static void Execute(IDbConnection connection, IDbTransaction transaction, string script, IDictionary<string, object> parameters = null)
        {
            foreach (string statement in SplitStatements(script))
            {
                if (string.IsNullOrWhiteSpace(statement))
                    continue;

                using (IDbCommand command = connection.CreateCommand())
                {
                    command.Transaction = transaction;
                    command.CommandText = statement;
                    if (parameters != null)
                    {
                        foreach (KeyValuePair<string, object> parameter in parameters)
                            AddParameter(command, parameter.Key, parameter.Value);
                    }
                    command.ExecuteNonQuery();
                }
            }
        }

        private static void AddParameter(IDbCommand command, string name, object value)
        {
            IDbDataParameter parameter = command.CreateParameter();
            parameter.ParameterName = name;
            parameter.Value = value ?? DBNull.Value;
            command.Parameters.Add(parameter);
        }

        private static IEnumerable<string> SplitStatements(string script)
        {
            return script.Split(new[] { "\r\nGO\r\n", "\nGO\n", "\rGO\r" }, StringSplitOptions.RemoveEmptyEntries);
        }

        private static readonly SqlMigration[] Migrations =
        {
            new SqlMigration("202601010001_initial_production_schema", @"
IF OBJECT_ID(N'dbo.Mandanten', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Mandanten(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Mandanten PRIMARY KEY DEFAULT NEWID(),
        Name NVARCHAR(200) NOT NULL,
        IstAktiv BIT NOT NULL CONSTRAINT DF_Mandanten_IstAktiv DEFAULT 1,
        CONSTRAINT UQ_Mandanten_Name UNIQUE(Name)
    );
END
GO
IF OBJECT_ID(N'dbo.Abteilungen', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Abteilungen(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Abteilungen PRIMARY KEY DEFAULT NEWID(),
        MandantId UNIQUEIDENTIFIER NOT NULL,
        Name NVARCHAR(200) NOT NULL,
        CONSTRAINT FK_Abteilungen_Mandanten FOREIGN KEY(MandantId) REFERENCES dbo.Mandanten(Id),
        CONSTRAINT UQ_Abteilungen_Mandant_Name UNIQUE(MandantId, Name)
    );
END
GO
IF OBJECT_ID(N'dbo.Qualifikationen', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Qualifikationen(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Qualifikationen PRIMARY KEY DEFAULT NEWID(),
        MandantId UNIQUEIDENTIFIER NOT NULL,
        Name NVARCHAR(200) NOT NULL,
        CONSTRAINT FK_Qualifikationen_Mandanten FOREIGN KEY(MandantId) REFERENCES dbo.Mandanten(Id),
        CONSTRAINT UQ_Qualifikationen_Mandant_Name UNIQUE(MandantId, Name)
    );
END
GO
IF OBJECT_ID(N'dbo.Mitarbeiter', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Mitarbeiter(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Mitarbeiter PRIMARY KEY DEFAULT NEWID(),
        MandantId UNIQUEIDENTIFIER NOT NULL,
        AbteilungId UNIQUEIDENTIFIER NOT NULL,
        Name NVARCHAR(200) NOT NULL,
        WochenstundenLimit INT NOT NULL CONSTRAINT DF_Mitarbeiter_WochenstundenLimit DEFAULT 40,
        IstAktiv BIT NOT NULL CONSTRAINT DF_Mitarbeiter_IstAktiv DEFAULT 1,
        CONSTRAINT FK_Mitarbeiter_Mandanten FOREIGN KEY(MandantId) REFERENCES dbo.Mandanten(Id),
        CONSTRAINT FK_Mitarbeiter_Abteilungen FOREIGN KEY(AbteilungId) REFERENCES dbo.Abteilungen(Id),
        CONSTRAINT CK_Mitarbeiter_WochenstundenLimit CHECK(WochenstundenLimit BETWEEN 0 AND 168),
        CONSTRAINT UQ_Mitarbeiter_Mandant_Name UNIQUE(MandantId, Name)
    );
END
GO
IF OBJECT_ID(N'dbo.MitarbeiterQualifikationen', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.MitarbeiterQualifikationen(
        MitarbeiterId UNIQUEIDENTIFIER NOT NULL,
        QualifikationId UNIQUEIDENTIFIER NOT NULL,
        CONSTRAINT PK_MitarbeiterQualifikationen PRIMARY KEY(MitarbeiterId, QualifikationId),
        CONSTRAINT FK_MitarbeiterQualifikationen_Mitarbeiter FOREIGN KEY(MitarbeiterId) REFERENCES dbo.Mitarbeiter(Id) ON DELETE CASCADE,
        CONSTRAINT FK_MitarbeiterQualifikationen_Qualifikationen FOREIGN KEY(QualifikationId) REFERENCES dbo.Qualifikationen(Id)
    );
END
GO
IF OBJECT_ID(N'dbo.Schichten', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Schichten(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Schichten PRIMARY KEY DEFAULT NEWID(),
        MandantId UNIQUEIDENTIFIER NOT NULL,
        AbteilungId UNIQUEIDENTIFIER NOT NULL,
        BenoetigteQualifikationId UNIQUEIDENTIFIER NULL,
        Name NVARCHAR(200) NOT NULL,
        Wochentag NVARCHAR(40) NOT NULL,
        Start DATETIME2 NOT NULL,
        Ende DATETIME2 NOT NULL,
        BenoetigteMitarbeiter INT NOT NULL,
        CONSTRAINT FK_Schichten_Mandanten FOREIGN KEY(MandantId) REFERENCES dbo.Mandanten(Id),
        CONSTRAINT FK_Schichten_Abteilungen FOREIGN KEY(AbteilungId) REFERENCES dbo.Abteilungen(Id),
        CONSTRAINT FK_Schichten_Qualifikationen FOREIGN KEY(BenoetigteQualifikationId) REFERENCES dbo.Qualifikationen(Id),
        CONSTRAINT CK_Schichten_Zeitraum CHECK(Ende > Start),
        CONSTRAINT CK_Schichten_Kapazitaet CHECK(BenoetigteMitarbeiter > 0),
        CONSTRAINT UQ_Schichten_Mandant_Name_Start UNIQUE(MandantId, Name, Start)
    );
END
GO
IF OBJECT_ID(N'dbo.Zuweisungen', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Zuweisungen(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Zuweisungen PRIMARY KEY DEFAULT NEWID(),
        MandantId UNIQUEIDENTIFIER NOT NULL,
        MitarbeiterId UNIQUEIDENTIFIER NOT NULL,
        SchichtId UNIQUEIDENTIFIER NOT NULL,
        ErstelltAm DATETIME2 NOT NULL CONSTRAINT DF_Zuweisungen_ErstelltAm DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_Zuweisungen_Mandanten FOREIGN KEY(MandantId) REFERENCES dbo.Mandanten(Id),
        CONSTRAINT FK_Zuweisungen_Mitarbeiter FOREIGN KEY(MitarbeiterId) REFERENCES dbo.Mitarbeiter(Id),
        CONSTRAINT FK_Zuweisungen_Schichten FOREIGN KEY(SchichtId) REFERENCES dbo.Schichten(Id) ON DELETE CASCADE,
        CONSTRAINT UQ_Zuweisungen_Mitarbeiter_Schicht UNIQUE(MitarbeiterId, SchichtId)
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Zuweisungen_Schicht' AND object_id = OBJECT_ID(N'dbo.Zuweisungen'))
    CREATE INDEX IX_Zuweisungen_Schicht ON dbo.Zuweisungen(SchichtId)
GO
IF OBJECT_ID(N'dbo.Verfuegbarkeiten', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Verfuegbarkeiten(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Verfuegbarkeiten PRIMARY KEY DEFAULT NEWID(),
        MandantId UNIQUEIDENTIFIER NOT NULL,
        MitarbeiterId UNIQUEIDENTIFIER NOT NULL,
        Von DATETIME2 NOT NULL,
        Bis DATETIME2 NOT NULL,
        CONSTRAINT FK_Verfuegbarkeiten_Mandanten FOREIGN KEY(MandantId) REFERENCES dbo.Mandanten(Id),
        CONSTRAINT FK_Verfuegbarkeiten_Mitarbeiter FOREIGN KEY(MitarbeiterId) REFERENCES dbo.Mitarbeiter(Id) ON DELETE CASCADE,
        CONSTRAINT CK_Verfuegbarkeiten_Zeitraum CHECK(Bis > Von),
        CONSTRAINT UQ_Verfuegbarkeiten_Mitarbeiter_Zeitraum UNIQUE(MitarbeiterId, Von, Bis)
    );
END
GO
IF OBJECT_ID(N'dbo.Abwesenheiten', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Abwesenheiten(
        Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Abwesenheiten PRIMARY KEY DEFAULT NEWID(),
        MandantId UNIQUEIDENTIFIER NOT NULL,
        MitarbeiterId UNIQUEIDENTIFIER NOT NULL,
        Von DATETIME2 NOT NULL,
        Bis DATETIME2 NOT NULL,
        Grund NVARCHAR(500) NULL,
        CONSTRAINT FK_Abwesenheiten_Mandanten FOREIGN KEY(MandantId) REFERENCES dbo.Mandanten(Id),
        CONSTRAINT FK_Abwesenheiten_Mitarbeiter FOREIGN KEY(MitarbeiterId) REFERENCES dbo.Mitarbeiter(Id) ON DELETE CASCADE,
        CONSTRAINT CK_Abwesenheiten_Zeitraum CHECK(Bis > Von),
        CONSTRAINT UQ_Abwesenheiten_Mitarbeiter_Zeitraum UNIQUE(MitarbeiterId, Von, Bis)
    );
END"),
            new SqlMigration("202601010002_assignment_guards", @"
IF OBJECT_ID(N'dbo.trg_Zuweisungen_Validate', N'TR') IS NOT NULL
    DROP TRIGGER dbo.trg_Zuweisungen_Validate
GO
CREATE TRIGGER dbo.trg_Zuweisungen_Validate
ON dbo.Zuweisungen
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Mitarbeiter m ON m.Id = i.MitarbeiterId
        JOIN dbo.Schichten s ON s.Id = i.SchichtId
        WHERE m.MandantId <> i.MandantId OR s.MandantId <> i.MandantId
    )
    BEGIN
        THROW 51000, 'Zuweisung verletzt Mandantengrenzen.', 1;
    END;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Schichten s ON s.Id = i.SchichtId
        JOIN dbo.Zuweisungen z ON z.SchichtId = s.Id
        GROUP BY i.SchichtId, s.BenoetigteMitarbeiter
        HAVING COUNT(z.Id) > s.BenoetigteMitarbeiter
    )
    BEGIN
        THROW 51001, 'Schichtkapazitaet ueberschritten.', 1;
    END;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Schichten s ON s.Id = i.SchichtId
        JOIN dbo.Zuweisungen z ON z.MitarbeiterId = i.MitarbeiterId AND z.Id <> i.Id
        JOIN dbo.Schichten otherShift ON otherShift.Id = z.SchichtId
        WHERE s.Start < otherShift.Ende AND s.Ende > otherShift.Start
    )
    BEGIN
        THROW 51002, 'Mitarbeiter ist bereits in einer ueberlappenden Schicht eingeplant.', 1;
    END;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Schichten s ON s.Id = i.SchichtId
        LEFT JOIN dbo.MitarbeiterQualifikationen mq
            ON mq.MitarbeiterId = i.MitarbeiterId
            AND mq.QualifikationId = s.BenoetigteQualifikationId
        WHERE s.BenoetigteQualifikationId IS NOT NULL AND mq.MitarbeiterId IS NULL
    )
    BEGIN
        THROW 51003, 'Mitarbeiter besitzt die benoetigte Qualifikation nicht.', 1;
    END;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Schichten s ON s.Id = i.SchichtId
        JOIN dbo.Abwesenheiten a ON a.MitarbeiterId = i.MitarbeiterId
        WHERE s.Start < a.Bis AND s.Ende > a.Von
    )
    BEGIN
        THROW 51004, 'Mitarbeiter ist im Schichtzeitraum abwesend.', 1;
    END;
END")
        };
    }
}
