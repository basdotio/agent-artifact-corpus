"""
Root Cause Analysis (RCA) classification and vocabulary mapping rules.
"""

from typing import Any

# Standard OCPP StopTransaction reasons mapped to RCA Category & plain-language details
STOP_REASON_RULES: dict[str, dict[str, str]] = {
    "EVDisconnected": {
        "category": "USER_ACTION",
        "root_cause": "Premature Vehicle Disconnection",
        "explanation": "The vehicle was unplugged or disconnected before normal charging completion.",
        "recommendation": "Advise driver to stop session via app/screen before removing connector."
    },
    "EmergencyStop": {
        "category": "SAFETY_TRIGGER",
        "root_cause": "Emergency Stop Button Pressed",
        "explanation": "The physical emergency stop button on the charging station was activated.",
        "recommendation": "Inspect station to verify physical E-stop button has been released and no physical hazard exists."
    },
    "PowerLoss": {
        "category": "GRID_OR_POWER_FAULT",
        "root_cause": "AC Mains Grid Power Loss",
        "explanation": "The charging station experienced a sudden loss of AC mains power.",
        "recommendation": "Check upstream circuit breaker / electrical panel and verify grid stability at location."
    },
    "Local": {
        "category": "USER_ACTION",
        "root_cause": "Session Stopped at Charger",
        "explanation": "The session was manually terminated at the charger interface (touchscreen or RFID tap).",
        "recommendation": "Normal user-initiated termination."
    },
    "Remote": {
        "category": "APP_OR_SERVER_ACTION",
        "root_cause": "Remote Stop Command",
        "explanation": "The session was stopped remotely via the driver mobile app or CMS backend command.",
        "recommendation": "Verify if user intentionally tapped 'Stop' in the mobile app."
    },
    "DeAuthorized": {
        "category": "AUTHENTICATION_ISSUE",
        "root_cause": "User Authorization Revoked",
        "explanation": "The RFID tag or user account was de-authorized by the server during charging.",
        "recommendation": "Check user wallet balance, subscription status, or payment method authorization."
    },
    "HardReset": {
        "category": "CHARGER_REBOOT",
        "root_cause": "Hard Reset Initiated",
        "explanation": "The charger hardware executed a hard reboot while the transaction was in progress.",
        "recommendation": "Inspect charger firmware logs to determine reboot trigger; schedule preventative maintenance."
    },
    "SoftReset": {
        "category": "CHARGER_REBOOT",
        "root_cause": "Soft Reset Initiated",
        "explanation": "The charger executed a software reset/restart while active.",
        "recommendation": "Check CMS maintenance schedules or over-the-air firmware update jobs."
    },
    "Reboot": {
        "category": "CHARGER_REBOOT",
        "root_cause": "Charger Rebooted",
        "explanation": "The station rebooted during active charging.",
        "recommendation": "Monitor charger uptime and verify power supply units (PSU)."
    },
    "UnlockCommand": {
        "category": "OPERATIONAL_ACTION",
        "root_cause": "Cable Unlock Triggered",
        "explanation": "An unlock connector command was executed, forcing the session to abort.",
        "recommendation": "Verify why an unlock was commanded during an active session."
    },
    "Other": {
        "category": "UNCLASSIFIED_VENDOR",
        "root_cause": "Vendor-Specific Other Reason",
        "explanation": "Charger reported 'Other' as stop reason without specific standard subcode.",
        "recommendation": "Check connector status logs and vendor controller logs for detailed internal codes."
    }
}

# Standard OCPP StatusNotification errorCodes mapped to RCA Category & plain-language details
ERROR_CODE_RULES: dict[str, dict[str, str]] = {
    "ConnectorLockFailure": {
        "category": "HARDWARE_FAULT",
        "root_cause": "Connector Solenoid Lock Failure",
        "explanation": "The mechanical lock mechanism failed to secure the charging gun into the EV socket.",
        "recommendation": "Inspect connector locking pin and solenoid for mechanical obstruction or wear."
    },
    "EVCommunicationError": {
        "category": "EV_COMMUNICATION_FAULT",
        "root_cause": "EV Communication Protocol Failure",
        "explanation": "Handshake failure between EV and charger (e.g. CAN bus or PLC pilot signal timeout).",
        "recommendation": "Try reconnecting; if persistent across multiple EVs, check charger pilot line / controller board."
    },
    "GroundFailure": {
        "category": "ELECTRICAL_SAFETY_FAULT",
        "root_cause": "Earth / Ground Fault Detected",
        "explanation": "Station detected unsafe grounding or leakage current tripping protective earth interlocks.",
        "recommendation": "High priority: Dispatch field technician to test earth resistance and residual current device (RCD)."
    },
    "HighTemperature": {
        "category": "THERMAL_FAULT",
        "root_cause": "Thermal Limit Exceeded",
        "explanation": "Temperature inside the power converter or at the connector pins exceeded safety limits.",
        "recommendation": "Check cooling fans, air filters, and connector pin cleanliness."
    },
    "OverCurrentFailure": {
        "category": "ELECTRICAL_FAULT",
        "root_cause": "Overcurrent Protection Tripped",
        "explanation": "Current draw exceeded maximum allowed threshold for the connector or station.",
        "recommendation": "Inspect vehicle charging parameters and charger current calibration."
    },
    "PowerMeterFailure": {
        "category": "HARDWARE_FAULT",
        "root_cause": "Energy Meter Communication Failure",
        "explanation": "Charger lost RS-485 / Modbus communication with internal energy meter.",
        "recommendation": "Verify energy meter wiring and Modbus addressing."
    },
    "PowerSwitchFailure": {
        "category": "HARDWARE_FAULT",
        "root_cause": "Contactor / Power Switch Failure",
        "explanation": "Main AC contactor or DC power relay failed to engage or weld-check failed.",
        "recommendation": "Dispatch technician to check contactor coil voltage and auxiliary contacts."
    },
    "ReaderFailure": {
        "category": "HARDWARE_FAULT",
        "root_cause": "RFID / Card Reader Failure",
        "explanation": "RFID scanner or payment card terminal is unresponsive.",
        "recommendation": "Reboot card reader module or inspect reader cable harness."
    },
    "UnderVoltage": {
        "category": "GRID_FAULT",
        "root_cause": "AC Grid Undervoltage",
        "explanation": "Incoming grid AC voltage dropped below acceptable operational tolerance.",
        "recommendation": "Verify incoming mains supply voltage; contact local DISCOM / utility provider if recurring."
    },
    "OverVoltage": {
        "category": "GRID_FAULT",
        "root_cause": "AC Grid Overvoltage",
        "explanation": "Incoming grid AC voltage exceeded maximum rating.",
        "recommendation": "Check distribution transformer tap settings and surge protection."
    },
    "WeakSignal": {
        "category": "NETWORK_FAULT",
        "root_cause": "Weak Cellular / Network Signal",
        "explanation": "Cellular modem signal dropped, causing communication timeout with CMS.",
        "recommendation": "Check external GSM antenna positioning and signal strength."
    },
    "InternalError": {
        "category": "HARDWARE_FAULT",
        "root_cause": "Charger Internal Controller Error",
        "explanation": "Internal firmware exception or controller hardware error.",
        "recommendation": "Review vendor diagnostics and apply firmware patch if available."
    }
}


def classify_stop_reason(reason: str | None) -> dict[str, str] | None:
    """Look up classification for a StopTransaction.reason."""
    if not reason:
        return None
    # Normalize
    for k, v in STOP_REASON_RULES.items():
        if k.lower() == reason.strip().lower():
            return v
    return None


def classify_error_code(error_code: str | None) -> dict[str, str] | None:
    """Look up classification for a StatusNotification.errorCode."""
    if not error_code or error_code.strip().lower() in ("noerror", "none", "null", ""):
        return None
    for k, v in ERROR_CODE_RULES.items():
        if k.lower() == error_code.strip().lower():
            return v
    return None
