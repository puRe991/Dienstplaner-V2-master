using Dienstplaner.Infrastructure.Services;
using Dienstplaner.Models;

namespace Dienstplaner.Services
{
    public class ZuweisungsService
    {
        private readonly DienstplanDataService _dataService;

        public ZuweisungsService()
            : this(new DienstplanDataService())
        {
        }

        public ZuweisungsService(DienstplanDataService dataService)
        {
            _dataService = dataService;
        }

        public string Zuweisen(Mitarbeiter m, Schicht s)
        {
            return _dataService.Zuweisen(m, s);
        }
    }
}
