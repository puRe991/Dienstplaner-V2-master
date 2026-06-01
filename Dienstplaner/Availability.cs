using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace Dienstplaner.Models
{
    public enum RequestStatus
    {
        Draft,
        Submitted,
        Approved,
        Rejected,
        Cancelled
    }

    public enum ApprovalRole
    {
        Mitarbeiter,
        Filialleiter,
        Planer
    }

    public class DecisionLogEntry
    {
        public int Id { get; set; }
        public string AntragTyp { get; set; }
        public int AntragId { get; set; }
        public RequestStatus NeuerStatus { get; set; }
        public string Benutzer { get; set; }
        public ApprovalRole Rolle { get; set; }
        public DateTime Zeitpunkt { get; set; }
        public string Kommentar { get; set; }
    }

    public abstract class EmployeeRequest : INotifyPropertyChanged
    {
        private RequestStatus _status;
        private DateTime _aktualisiertAm;
        public int Id { get; set; }
        public int MitarbeiterId { get; set; }
        public string MitarbeiterName { get; set; }
        public RequestStatus Status
        {
            get { return _status; }
            set
            {
                _status = value;
                OnPropertyChanged();
            }
        }

        public DateTime ErstelltAm { get; set; }

        public DateTime AktualisiertAm
        {
            get { return _aktualisiertAm; }
            set
            {
                _aktualisiertAm = value;
                OnPropertyChanged();
            }
        }
        public string Kommentar { get; set; }

        protected EmployeeRequest()
        {
            Status = RequestStatus.Draft;
            ErstelltAm = DateTime.Now;
            AktualisiertAm = DateTime.Now;
        }

        public event PropertyChangedEventHandler PropertyChanged;

        protected void OnPropertyChanged([CallerMemberName] string name = null)
        {
            var handler = PropertyChanged;
            if (handler != null)
                handler(this, new PropertyChangedEventArgs(name));
        }
    }

    public class Availability : EmployeeRequest
    {
        public string Wochentag { get; set; }
        public TimeSpan Von { get; set; }
        public TimeSpan Bis { get; set; }
        public bool IstBevorzugt { get; set; }

        public string Zeitraum
        {
            get { return string.Format("{0:hh\\:mm}-{1:hh\\:mm}", Von, Bis); }
        }

        public bool DecktSchichtAb(Schicht schicht)
        {
            if (schicht == null || Status != RequestStatus.Approved)
                return false;

            if (!string.IsNullOrEmpty(Wochentag) && !string.IsNullOrEmpty(schicht.Wochentag) &&
                !string.Equals(Wochentag, schicht.Wochentag, StringComparison.OrdinalIgnoreCase))
                return false;

            if (Von == TimeSpan.Zero && Bis == TimeSpan.Zero)
                return true;

            return Von <= schicht.Start.TimeOfDay && Bis >= schicht.Ende.TimeOfDay;
        }
    }

    public abstract class Absence : EmployeeRequest
    {
        public DateTime Von { get; set; }
        public DateTime Bis { get; set; }
        public string Grund { get; set; }

        public bool Ueberschneidet(Schicht schicht)
        {
            if (schicht == null || Status != RequestStatus.Approved)
                return false;

            return Von < schicht.Ende && Bis > schicht.Start;
        }
    }

    public class LeaveRequest : Absence
    {
        public bool IstBezahlt { get; set; }
    }

    public class SickLeave : Absence
    {
        public bool ArbeitsunfaehigkeitsBescheinigungVorhanden { get; set; }
    }

    public class ShiftSwapRequest : EmployeeRequest
    {
        public int VonMitarbeiterId { get; set; }
        public string VonMitarbeiterName { get; set; }
        public int ZuMitarbeiterId { get; set; }
        public string ZuMitarbeiterName { get; set; }
        public int SchichtId { get; set; }
        public string SchichtName { get; set; }
    }

    public class ApprovalService
    {
        private int _naechsteLogId = 1;

        public bool DarfEntscheiden(ApprovalRole rolle)
        {
            return rolle == ApprovalRole.Filialleiter || rolle == ApprovalRole.Planer;
        }

        public DecisionLogEntry Entscheiden(EmployeeRequest request, RequestStatus neuerStatus, string benutzer, ApprovalRole rolle, string kommentar)
        {
            if (request == null)
                return null;

            if (!DarfEntscheiden(rolle))
                return null;

            if (neuerStatus != RequestStatus.Approved && neuerStatus != RequestStatus.Rejected && neuerStatus != RequestStatus.Cancelled)
                return null;

            request.Status = neuerStatus;
            request.AktualisiertAm = DateTime.Now;

            return new DecisionLogEntry
            {
                Id = _naechsteLogId++,
                AntragTyp = request.GetType().Name,
                AntragId = request.Id,
                NeuerStatus = neuerStatus,
                Benutzer = benutzer,
                Rolle = rolle,
                Zeitpunkt = DateTime.Now,
                Kommentar = kommentar
            };
        }
    }
}
