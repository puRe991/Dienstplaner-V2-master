"""Python implementation of the Dienstplaner application."""

from .models import Employee, LicenseInfo, Shift
from .services import SchedulerService

__version__ = "0.5.0"

__all__ = ["Employee", "LicenseInfo", "Shift", "SchedulerService", "__version__"]
