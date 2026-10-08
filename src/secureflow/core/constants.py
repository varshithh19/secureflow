"""SecureFlow Core System Constants and Safety Constraints.

Matches Section 1, 4, 7 of the specification.
"""
from typing import Dict, List, Tuple

# Safety validation limits for traffic signal intervals (in seconds) (SAFE)
SAFE_NS: Tuple[int, int] = (10, 120)
SAFE_EW: Tuple[int, int] = (10, 120)
SAFE_YELLOW: Tuple[int, int] = (3, 5)
SAFE_ALLRED: Tuple[int, int] = (1, 5)
SAFE_MAX_CYCLE: int = 240

# Standard Signal Sequence & Phase Names
SIGNAL_SEQUENCE = ["NS", "Y1", "R1", "EW", "Y2", "R2"]
PHASE_NAMES = {
    "NS": "North-south green",
    "Y1": "North-south amber",
    "R1": "All red",
    "EW": "East-west green",
    "Y2": "East-west amber",
    "R2": "All red",
}

# Role Definitions
ROLE_OPERATOR = "operator"
ROLE_SUPERVISOR = "supervisor"
ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_AUDITOR = "auditor"
ROLE_DISPATCHER = "emergency_dispatcher"
ROLE_SENSOR = "sensor_identity"

ROLES = {
    ROLE_OPERATOR: "Operator",
    ROLE_SUPERVISOR: "Supervisor",
    ROLE_ADMIN: "Administrator",
    ROLE_ANALYST: "Analyst",
    ROLE_AUDITOR: "Auditor",
    ROLE_DISPATCHER: "Emergency dispatcher",
}

# Canonical Permission Matrix (PERMS)
# Deny by default: any role not listed is denied.
PERMS: Dict[str, List[str]] = {
    "dashboard.view": [
        ROLE_OPERATOR,
        ROLE_SUPERVISOR,
        ROLE_ADMIN,
        ROLE_ANALYST,
        ROLE_AUDITOR,
        ROLE_DISPATCHER,
    ],
    "signal.view": [ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN],
    "signal.propose": [ROLE_OPERATOR, ROLE_SUPERVISOR],
    "signal.approve": [ROLE_SUPERVISOR],
    "emergency.view": [ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN, ROLE_DISPATCHER],
    "emergency.create": [ROLE_DISPATCHER],
    "emergency.cancel": [ROLE_DISPATCHER, ROLE_SUPERVISOR],
    "incident.view": [ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN],
    "incident.write": [ROLE_OPERATOR, ROLE_SUPERVISOR],
    "alert.view": [ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN],
    "analytics.view": [ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN, ROLE_ANALYST],
    "sensor.view": [ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN],
    "sensor.manage": [ROLE_ADMIN],
    "user.manage": [ROLE_ADMIN],
    "audit.view": [ROLE_ADMIN, ROLE_AUDITOR],
    "security.view": [ROLE_SUPERVISOR, ROLE_ADMIN, ROLE_AUDITOR],
    "security.simulate": [ROLE_SUPERVISOR, ROLE_ADMIN],
}

# 9 Canonical Junctions (J-01 to J-09)
DEFAULT_JUNCTIONS = [
    {"id": "J-01", "name": "Central Plaza", "x": 100, "y": 80, "base": 0.45},
    {"id": "J-02", "name": "Harbour Road", "x": 300, "y": 80, "base": 0.38},
    {"id": "J-03", "name": "Tech Park Gate", "x": 500, "y": 80, "base": 0.70},
    {"id": "J-04", "name": "Old Market", "x": 100, "y": 210, "base": 0.55},
    {"id": "J-05", "name": "Station Square", "x": 300, "y": 210, "base": 0.84},
    {"id": "J-06", "name": "University Gate", "x": 500, "y": 210, "base": 0.50},
    {"id": "J-07", "name": "Riverside", "x": 100, "y": 340, "base": 0.25},
    {"id": "J-08", "name": "Airport Link", "x": 300, "y": 340, "base": 0.40},
    {"id": "J-09", "name": "Hospital Cross", "x": 500, "y": 340, "base": 0.60},
]

# 12 Road Edges connecting junctions
ROAD_EDGES: List[Tuple[str, str]] = [
    ("J-01", "J-02"),
    ("J-02", "J-03"),
    ("J-04", "J-05"),
    ("J-05", "J-06"),
    ("J-07", "J-08"),
    ("J-08", "J-09"),
    ("J-01", "J-04"),
    ("J-04", "J-07"),
    ("J-02", "J-05"),
    ("J-05", "J-08"),
    ("J-03", "J-06"),
    ("J-06", "J-09"),
]

# Default Seed Sensors (SN-101 to SN-112)
DEFAULT_SENSORS = [
    {"id": "SN-101", "type": "camera", "jid": "J-01", "status": "ACTIVE", "loc": "Approach N"},
    {"id": "SN-102", "type": "loop", "jid": "J-02", "status": "ACTIVE", "loc": "Approach E"},
    {"id": "SN-103", "type": "radar", "jid": "J-03", "status": "ACTIVE", "loc": "Approach S"},
    {"id": "SN-104", "type": "camera", "jid": "J-04", "status": "ACTIVE", "loc": "Approach W"},
    {"id": "SN-105", "type": "camera", "jid": "J-05", "status": "ACTIVE", "loc": "Approach N"},
    {"id": "SN-106", "type": "loop", "jid": "J-05", "status": "ACTIVE", "loc": "Approach E"},
    {"id": "SN-107", "type": "radar", "jid": "J-06", "status": "ACTIVE", "loc": "Approach S"},
    {"id": "SN-108", "type": "loop", "jid": "J-07", "status": "ACTIVE", "loc": "Approach W"},
    {"id": "SN-109", "type": "camera", "jid": "J-07", "status": "REVOKED", "loc": "Approach N"},
    {"id": "SN-110", "type": "radar", "jid": "J-08", "status": "ACTIVE", "loc": "Approach E"},
    {"id": "SN-111", "type": "camera", "jid": "J-09", "status": "ACTIVE", "loc": "Approach S"},
    {"id": "SN-112", "type": "loop", "jid": "J-09", "status": "PENDING", "loc": "Approach W"},
]
