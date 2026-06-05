using System;
using System.Net;
using System.Windows;
using Dienstplaner.Infrastructure;
using Dienstplaner.Infrastructure.Migrations;
using Dienstplaner.Infrastructure.Repositories;
using Dienstplaner.Infrastructure.Services;
using Dienstplaner.ViewModels;

namespace Dienstplaner
{
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            base.OnStartup(e);

            try
            {
                MainWindow = CreateMainWindow();
                MainWindow.Show();
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Dienstplaner konnte nicht gestartet werden. Die Datenbankverbindung oder die Datenbankmigration ist fehlgeschlagen. " +
                    "Bitte prüfen Sie die Verbindungszeichenfolge 'DienstplanerDb' und ob SQL Server erreichbar ist.\n\nTechnische Details: " + ex.Message,
                    "Startfehler",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
                Shutdown(1);
            }
        }

        private static MainWindow CreateMainWindow()
        {
            IDatabaseConnectionFactory connectionFactory = new SqlServerConnectionFactory("DienstplanerDb");
            var migrationRunner = new SqlServerMigrationRunner(connectionFactory);
            migrationRunner.Migrate();

            IDienstplanRepository repository = new SqlDienstplanRepository(connectionFactory);
            var dataService = new DienstplanDataService(repository);
            var viewModel = new MainViewModel(dataService);
            return new MainWindow(viewModel);
        }
    }
}
