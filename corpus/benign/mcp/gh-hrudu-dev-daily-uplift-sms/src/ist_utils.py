"""IST timezone utilities for Daily Uplift SMS"""
from datetime import datetime
import pytz

def get_ist_time():
    """Get current time in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def format_ist_time(dt=None):
    """Format IST time as readable string"""
    if dt is None:
        dt = get_ist_time()
    return dt.strftime("%A, %d %B %Y %H:%M:%S IST")

def get_ist_hour():
    """Get current hour in IST (0-23)"""
    return get_ist_time().hour

def is_business_hours():
    """Check if current IST time is business hours (9 AM - 6 PM)"""
    hour = get_ist_hour()
    return 9 <= hour <= 18