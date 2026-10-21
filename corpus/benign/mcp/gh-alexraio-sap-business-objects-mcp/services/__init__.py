"""
Domain services for SAP BusinessObjects 4.3 SP5 REST Web Services.
"""

from .admin_service import AdminService
from .infostore_service import InfostoreService
from .schedule_service import ScheduleService
from .universe_service import UniverseService
from .webi_service import WebiService

__all__ = [
    "WebiService",
    "UniverseService",
    "ScheduleService",
    "AdminService",
    "InfostoreService",
]
