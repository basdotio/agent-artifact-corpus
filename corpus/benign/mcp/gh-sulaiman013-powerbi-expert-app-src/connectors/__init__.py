"""
Power BI Connectors

These connectors handle the actual connection to Power BI:
- Desktop: Connect to running Power BI Desktop instances
- XMLA: Cloud XMLA endpoints for Power BI Service
- TOM: Tabular Object Model for write operations
- PBIP: Power BI Project file editing
- REST: Power BI REST API

The LLM layer generates DAX queries, these connectors execute them.
"""

from .desktop import PowerBIDesktopConnector
from .xmla import PowerBIXmlaConnector
from .tom import PowerBITOMConnector
from .pbip import PowerBIPBIPConnector
from .rest import PowerBIRestConnector

__all__ = [
    "PowerBIDesktopConnector",
    "PowerBIXmlaConnector",
    "PowerBITOMConnector",
    "PowerBIPBIPConnector",
    "PowerBIRestConnector",
]
