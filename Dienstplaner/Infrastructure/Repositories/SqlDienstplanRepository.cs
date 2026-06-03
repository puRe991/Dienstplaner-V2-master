using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using Dienstplaner.Models;

namespace Dienstplaner.Infrastructure.Repositories
{
    public class SqlDienstplanRepository : IDienstplanRepository
    {
        private readonly IDatabaseConnectionFactory _connectionFactory;

        public SqlDienstplanRepository(IDatabaseConnectionFactory connectionFactory)
        {
            _connectionFactory = connectionFactory;
        }

        public Guid EnsureMandant(string name)
        {
            using (IDbConnection connection = OpenConnection())
            using (IDbTransaction transaction = connection.BeginTransaction())
            {
                Guid id = EnsureNamedEntity(connection, transaction, "Mandanten", Guid.Empty, name);
                transaction.Commit();
                return id;
            }
        }

        public IList<Mitarbeiter> GetMitarbeiter(Guid mandantId)
        {
            Dictionary<Guid, Mitarbeiter> result = new Dictionary<Guid, Mitarbeiter>();
            using (IDbConnection connection = OpenConnection())
            using (IDbCommand command = connection.CreateCommand())
            {
                command.CommandText = @"
SELECT m.Id, m.Name, a.Name AS Abteilung, q.Name AS Qualifikation, m.WochenstundenLimit, m.IstAktiv
FROM dbo.Mitarbeiter m
JOIN dbo.Abteilungen a ON a.Id = m.AbteilungId
LEFT JOIN dbo.MitarbeiterQualifikationen mq ON mq.MitarbeiterId = m.Id
LEFT JOIN dbo.Qualifikationen q ON q.Id = mq.QualifikationId
WHERE m.MandantId = @MandantId
ORDER BY m.Name";
                AddParameter(command, "@MandantId", mandantId);

                using (IDataReader reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        Guid id = reader.GetGuid(0);
                        Mitarbeiter mitarbeiter;
                        if (!result.TryGetValue(id, out mitarbeiter))
                        {
                            mitarbeiter = new Mitarbeiter
                            {
                                DatabaseId = id,
                                Id = StableId(id),
                                Name = reader.GetString(1),
                                Abteilung = reader.GetString(2),
                                WochenstundenLimit = reader.GetInt32(4),
                                IstAktiv = reader.GetBoolean(5)
                            };
                            result.Add(id, mitarbeiter);
                        }

                        if (!reader.IsDBNull(3))
                            mitarbeiter.Qualifikation = reader.GetString(3);
                    }
                }
            }

            LoadAssignments(mandantId, result, null);
            return new List<Mitarbeiter>(result.Values);
        }

        public IList<Schicht> GetSchichten(Guid mandantId)
        {
            Dictionary<Guid, Schicht> result = new Dictionary<Guid, Schicht>();
            using (IDbConnection connection = OpenConnection())
            using (IDbCommand command = connection.CreateCommand())
            {
                command.CommandText = @"
SELECT s.Id, s.Name, a.Name AS Abteilung, s.Wochentag, s.Start, s.Ende, s.BenoetigteMitarbeiter, q.Name AS BenoetigteQualifikation
FROM dbo.Schichten s
JOIN dbo.Abteilungen a ON a.Id = s.AbteilungId
LEFT JOIN dbo.Qualifikationen q ON q.Id = s.BenoetigteQualifikationId
WHERE s.MandantId = @MandantId
ORDER BY s.Start, s.Name";
                AddParameter(command, "@MandantId", mandantId);

                using (IDataReader reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        result.Add(reader.GetGuid(0), new Schicht
                        {
                            DatabaseId = reader.GetGuid(0),
                            Id = StableId(reader.GetGuid(0)),
                            Name = reader.GetString(1),
                            Abteilung = reader.GetString(2),
                            Wochentag = reader.GetString(3),
                            Start = reader.GetDateTime(4),
                            Ende = reader.GetDateTime(5),
                            BenoetigteMitarbeiter = reader.GetInt32(6),
                            BenoetigteQualifikation = reader.IsDBNull(7) ? null : reader.GetString(7)
                        });
                    }
                }
            }

            LoadAssignments(mandantId, null, result);
            return new List<Schicht>(result.Values);
        }

        public Mitarbeiter AddMitarbeiter(Guid mandantId, string name, string abteilung, string qualifikation, int wochenstundenLimit)
        {
            if (string.IsNullOrWhiteSpace(name))
                throw new ArgumentException("Name ist erforderlich.", "name");
            if (string.IsNullOrWhiteSpace(abteilung))
                throw new ArgumentException("Abteilung ist erforderlich.", "abteilung");

            using (IDbConnection connection = OpenConnection())
            using (IDbTransaction transaction = connection.BeginTransaction(IsolationLevel.Serializable))
            {
                Guid abteilungId = EnsureNamedEntity(connection, transaction, "Abteilungen", mandantId, abteilung);
                Guid mitarbeiterId = Guid.NewGuid();

                Execute(connection, transaction, @"
INSERT INTO dbo.Mitarbeiter(Id, MandantId, AbteilungId, Name, WochenstundenLimit, IstAktiv)
VALUES(@Id, @MandantId, @AbteilungId, @Name, @WochenstundenLimit, 1)",
                    Params("@Id", mitarbeiterId, "@MandantId", mandantId, "@AbteilungId", abteilungId, "@Name", name.Trim(), "@WochenstundenLimit", wochenstundenLimit));

                if (!string.IsNullOrWhiteSpace(qualifikation))
                {
                    Guid qualifikationId = EnsureNamedEntity(connection, transaction, "Qualifikationen", mandantId, qualifikation);
                    Execute(connection, transaction,
                        "INSERT INTO dbo.MitarbeiterQualifikationen(MitarbeiterId, QualifikationId) VALUES(@MitarbeiterId, @QualifikationId)",
                        Params("@MitarbeiterId", mitarbeiterId, "@QualifikationId", qualifikationId));
                }

                transaction.Commit();
                return new Mitarbeiter
                {
                    DatabaseId = mitarbeiterId,
                    Id = StableId(mitarbeiterId),
                    Name = name.Trim(),
                    Abteilung = abteilung.Trim(),
                    Qualifikation = string.IsNullOrWhiteSpace(qualifikation) ? null : qualifikation.Trim(),
                    WochenstundenLimit = wochenstundenLimit,
                    IstAktiv = true
                };
            }
        }

        public Schicht AddSchicht(Guid mandantId, string name, string abteilung, string wochentag, DateTime start, DateTime ende, int benoetigteMitarbeiter, string benoetigteQualifikation)
        {
            if (string.IsNullOrWhiteSpace(name))
                throw new ArgumentException("Schichtname ist erforderlich.", "name");
            if (string.IsNullOrWhiteSpace(abteilung))
                throw new ArgumentException("Abteilung ist erforderlich.", "abteilung");
            if (ende <= start)
                throw new ArgumentException("Schichtende muss nach dem Start liegen.", "ende");
            if (benoetigteMitarbeiter <= 0)
                throw new ArgumentException("Kapazität muss größer als 0 sein.", "benoetigteMitarbeiter");

            using (IDbConnection connection = OpenConnection())
            using (IDbTransaction transaction = connection.BeginTransaction(IsolationLevel.Serializable))
            {
                Guid abteilungId = EnsureNamedEntity(connection, transaction, "Abteilungen", mandantId, abteilung);
                Guid? qualifikationId = null;
                if (!string.IsNullOrWhiteSpace(benoetigteQualifikation))
                    qualifikationId = EnsureNamedEntity(connection, transaction, "Qualifikationen", mandantId, benoetigteQualifikation);

                Guid schichtId = Guid.NewGuid();
                Execute(connection, transaction, @"
INSERT INTO dbo.Schichten(Id, MandantId, AbteilungId, BenoetigteQualifikationId, Name, Wochentag, Start, Ende, BenoetigteMitarbeiter)
VALUES(@Id, @MandantId, @AbteilungId, @BenoetigteQualifikationId, @Name, @Wochentag, @Start, @Ende, @BenoetigteMitarbeiter)",
                    Params("@Id", schichtId, "@MandantId", mandantId, "@AbteilungId", abteilungId, "@BenoetigteQualifikationId", (object)qualifikationId ?? DBNull.Value,
                        "@Name", name.Trim(), "@Wochentag", string.IsNullOrWhiteSpace(wochentag) ? start.DayOfWeek.ToString() : wochentag.Trim(),
                        "@Start", start, "@Ende", ende, "@BenoetigteMitarbeiter", benoetigteMitarbeiter));

                transaction.Commit();
                return new Schicht
                {
                    DatabaseId = schichtId,
                    Id = StableId(schichtId),
                    Name = name.Trim(),
                    Abteilung = abteilung.Trim(),
                    Wochentag = string.IsNullOrWhiteSpace(wochentag) ? start.DayOfWeek.ToString() : wochentag.Trim(),
                    Start = start,
                    Ende = ende,
                    BenoetigteMitarbeiter = benoetigteMitarbeiter,
                    BenoetigteQualifikation = string.IsNullOrWhiteSpace(benoetigteQualifikation) ? null : benoetigteQualifikation.Trim()
                };
            }
        }

        public string Assign(Guid mandantId, Guid mitarbeiterId, Guid schichtId)
        {
            try
            {
                using (IDbConnection connection = OpenConnection())
                using (IDbTransaction transaction = connection.BeginTransaction(IsolationLevel.Serializable))
                {
                    Execute(connection, transaction,
                        "INSERT INTO dbo.Zuweisungen(Id, MandantId, MitarbeiterId, SchichtId) VALUES(@Id, @MandantId, @MitarbeiterId, @SchichtId)",
                        Params("@Id", Guid.NewGuid(), "@MandantId", mandantId, "@MitarbeiterId", mitarbeiterId, "@SchichtId", schichtId));
                    transaction.Commit();
                }

                return "Zuweisung erfolgreich";
            }
            catch (SqlException ex)
            {
                return ex.Message;
            }
        }

        public void DeleteSchicht(Guid mandantId, Guid schichtId)
        {
            using (IDbConnection connection = OpenConnection())
            {
                Execute(connection, null,
                    "DELETE FROM dbo.Schichten WHERE MandantId = @MandantId AND Id = @SchichtId",
                    Params("@MandantId", mandantId, "@SchichtId", schichtId));
            }
        }

        public bool HasAnyData(Guid mandantId)
        {
            using (IDbConnection connection = OpenConnection())
            using (IDbCommand command = connection.CreateCommand())
            {
                command.CommandText = "SELECT COUNT(1) FROM dbo.Mitarbeiter WHERE MandantId = @MandantId";
                AddParameter(command, "@MandantId", mandantId);
                return Convert.ToInt32(command.ExecuteScalar()) > 0;
            }
        }

        private void LoadAssignments(Guid mandantId, IDictionary<Guid, Mitarbeiter> mitarbeiter, IDictionary<Guid, Schicht> schichten)
        {
            using (IDbConnection connection = OpenConnection())
            using (IDbCommand command = connection.CreateCommand())
            {
                command.CommandText = @"
SELECT z.MitarbeiterId, z.SchichtId, m.Name, s.Name, a.Name, s.Wochentag, s.Start, s.Ende, s.BenoetigteMitarbeiter, q.Name
FROM dbo.Zuweisungen z
JOIN dbo.Mitarbeiter m ON m.Id = z.MitarbeiterId
JOIN dbo.Schichten s ON s.Id = z.SchichtId
JOIN dbo.Abteilungen a ON a.Id = s.AbteilungId
LEFT JOIN dbo.Qualifikationen q ON q.Id = s.BenoetigteQualifikationId
WHERE z.MandantId = @MandantId";
                AddParameter(command, "@MandantId", mandantId);

                using (IDataReader reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        Guid mitarbeiterId = reader.GetGuid(0);
                        Guid schichtId = reader.GetGuid(1);
                        string mitarbeiterName = reader.GetString(2);

                        if (schichten != null && schichten.ContainsKey(schichtId))
                            schichten[schichtId].MitarbeiterNamen.Add(mitarbeiterName);

                        if (mitarbeiter != null && mitarbeiter.ContainsKey(mitarbeiterId))
                        {
                            mitarbeiter[mitarbeiterId].Schichten.Add(new Schicht
                            {
                                DatabaseId = schichtId,
                                Id = StableId(schichtId),
                                Name = reader.GetString(3),
                                Abteilung = reader.GetString(4),
                                Wochentag = reader.GetString(5),
                                Start = reader.GetDateTime(6),
                                Ende = reader.GetDateTime(7),
                                BenoetigteMitarbeiter = reader.GetInt32(8),
                                BenoetigteQualifikation = reader.IsDBNull(9) ? null : reader.GetString(9)
                            });
                        }
                    }
                }
            }
        }

        private IDbConnection OpenConnection()
        {
            IDbConnection connection = _connectionFactory.CreateConnection();
            connection.Open();
            return connection;
        }

        private Guid EnsureNamedEntity(IDbConnection connection, IDbTransaction transaction, string table, Guid mandantId, string name)
        {
            string cleanName = name.Trim();
            string selectSql = table == "Mandanten"
                ? "SELECT Id FROM dbo.Mandanten WHERE Name = @Name"
                : "SELECT Id FROM dbo." + table + " WHERE MandantId = @MandantId AND Name = @Name";

            object existing = Scalar(connection, transaction, selectSql, Params("@MandantId", mandantId, "@Name", cleanName));
            if (existing != null && existing != DBNull.Value)
                return (Guid)existing;

            Guid id = Guid.NewGuid();
            string insertSql = table == "Mandanten"
                ? "INSERT INTO dbo.Mandanten(Id, Name, IstAktiv) VALUES(@Id, @Name, 1)"
                : "INSERT INTO dbo." + table + "(Id, MandantId, Name) VALUES(@Id, @MandantId, @Name)";
            Execute(connection, transaction, insertSql, Params("@Id", id, "@MandantId", mandantId, "@Name", cleanName));
            return id;
        }

        private static object Scalar(IDbConnection connection, IDbTransaction transaction, string sql, IDictionary<string, object> parameters)
        {
            using (IDbCommand command = connection.CreateCommand())
            {
                command.Transaction = transaction;
                command.CommandText = sql;
                AddParameters(command, parameters);
                return command.ExecuteScalar();
            }
        }

        private static void Execute(IDbConnection connection, IDbTransaction transaction, string sql, IDictionary<string, object> parameters)
        {
            using (IDbCommand command = connection.CreateCommand())
            {
                command.Transaction = transaction;
                command.CommandText = sql;
                AddParameters(command, parameters);
                command.ExecuteNonQuery();
            }
        }

        private static int StableId(Guid id)
        {
            byte[] bytes = id.ToByteArray();
            int value = BitConverter.ToInt32(bytes, 0) & int.MaxValue;
            return value == 0 ? 1 : value;
        }

        private static void AddParameters(IDbCommand command, IDictionary<string, object> parameters)
        {
            foreach (KeyValuePair<string, object> parameter in parameters)
                AddParameter(command, parameter.Key, parameter.Value);
        }

        private static void AddParameter(IDbCommand command, string name, object value)
        {
            IDbDataParameter parameter = command.CreateParameter();
            parameter.ParameterName = name;
            parameter.Value = value ?? DBNull.Value;
            command.Parameters.Add(parameter);
        }

        private static IDictionary<string, object> Params(params object[] values)
        {
            Dictionary<string, object> parameters = new Dictionary<string, object>();
            for (int i = 0; i < values.Length; i += 2)
                parameters.Add((string)values[i], values[i + 1]);
            return parameters;
        }
    }
}
