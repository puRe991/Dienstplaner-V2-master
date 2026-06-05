using System;
using System.Configuration;
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
            }
            catch (Exception ex)
            {
                MainWindow = CreateDemoMainWindow(ex);
            }

            MainWindow.Show();
        }

        private static MainWindow CreateMainWindow()
        {
            IDatabaseConnectionFactory connectionFactory = new SqlServerConnectionFactory("DienstplanerDb");
            var migrationRunner = new SqlServerMigrationRunner(connectionFactory);
            migrationRunner.Migrate();

            IDienstplanRepository repository = new SqlDienstplanRepository(connectionFactory);
            var dataService = new DienstplanDataService(repository);
            if (IsDemoModeEnabled())
                dataService.SeedDemoDataIfEmpty();

            var viewModel = new MainViewModel(dataService);
            return new MainWindow(viewModel);
        }

        private static MainWindow CreateDemoMainWindow(Exception startupException)
        {
            var viewModel = new MainViewModel();
            viewModel.StatusNachricht = "Demo-Modus aktiv: Datenbank nicht erreichbar (" + startupException.Message + ").";
            return new MainWindow(viewModel);
        }

        private static bool IsDemoModeEnabled()
        {
            bool enabled;
            return bool.TryParse(ConfigurationManager.AppSettings["DemoMode"], out enabled) && enabled;
        }
    }
}
