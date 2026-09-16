"""
SR22T Runway Brief - Reference Module Initialization

This makes it easy to import everything:
    from references import *

Or import specific items:
    from references import EMBEDDED_SR22T_PERFORMANCE, calculate_pressure_altitude
"""

# Import all performance data
from .sr22t_performance_data import EMBEDDED_SR22T_PERFORMANCE

# Import all calculation functions
from .calculation_functions import (
    calculate_pressure_altitude,
    calculate_isa_temperature,
    calculate_density_altitude,
    calculate_wind_components,
    interpolate_performance,
    assess_runway_margin
)

__all__ = [
    'EMBEDDED_SR22T_PERFORMANCE',
    'calculate_pressure_altitude',
    'calculate_isa_temperature',
    'calculate_density_altitude',
    'calculate_wind_components',
    'interpolate_performance',
    'assess_runway_margin',
]
