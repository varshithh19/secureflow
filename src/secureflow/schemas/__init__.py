"""SecureFlow Pydantic v2 Validation Schemas.

Enforces strict request validation and response shapes matching frontend contracts.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from secureflow.core.constants import SAFE_ALLRED, SAFE_EW, SAFE_MAX_CYCLE, SAFE_NS, SAFE_YELLOW


# Auth Schemas
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class MFARequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=6, max_length=6)


class UserSummary(BaseModel):
    id: str
    name: str
    role: str
    mfa: bool = False
    locked: bool = False
    fails: int = 0
    last: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    csrf_token: Optional[str] = None
    token_type: str = "bearer"
    mfa_required: bool = False
    name: Optional[str] = None
    role: Optional[str] = None
    user: Optional[UserSummary] = None


# Signal Plan & Timing Schemas (SR-04 / SAFE bounds)
class SignalTimingPlan(BaseModel):
    ns: int = Field(..., ge=SAFE_NS[0], le=SAFE_NS[1])
    ew: int = Field(..., ge=SAFE_EW[0], le=SAFE_EW[1])
    yellow: int = Field(..., ge=SAFE_YELLOW[0], le=SAFE_YELLOW[1])
    allred: int = Field(..., ge=SAFE_ALLRED[0], le=SAFE_ALLRED[1])

    @field_validator("allred")
    @classmethod
    def validate_total_cycle(cls, v: int, info) -> int:
        data = info.data
        if "ns" in data and "ew" in data and "yellow" in data:
            tot = data["ns"] + data["ew"] + 2 * (data["yellow"] + v)
            if tot > SAFE_MAX_CYCLE:
                raise ValueError(f"Cycle length {tot} s is above the {SAFE_MAX_CYCLE} s limit.")
        return v


class ProposeSignalRequest(BaseModel):
    jid: str = Field(..., min_length=2, max_length=20)
    plan: SignalTimingPlan
    reason: str = Field(..., min_length=10, max_length=200)


class DecideSignalRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    note: Optional[str] = Field(default="", max_length=200)


class SignalRequestResponse(BaseModel):
    id: str
    jid: str
    from_: SignalTimingPlan = Field(..., alias="from")
    plan: SignalTimingPlan
    reason: str
    by: str
    ts: int
    state: str
    approver: Optional[str] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Junction Schemas
class JunctionResponse(BaseModel):
    id: str
    name: str
    x: int
    y: int
    base: float
    occ: float
    speed: int
    count: int
    level: int
    mode: str
    plan: SignalTimingPlan
    pi: int
    rem: int
    corridor: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Emergency Corridor Schemas (SR-07 / FR-05)
class CreateEmergencyRequest(BaseModel):
    vehicle: str = Field(..., min_length=3, max_length=50)
    from_junction: str = Field(..., min_length=2, max_length=20)
    to_junction: str = Field(..., min_length=2, max_length=20)
    duration: int = Field(..., ge=60, le=300)
    reason: str = Field(..., min_length=3, max_length=100)


class CorridorResponse(BaseModel):
    id: str
    vehicle: str
    from_: str = Field(..., alias="from")
    to: str
    route: List[str]
    by: str
    ts: int
    expires: int
    state: str
    reason: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Incident Schemas
class CreateIncidentRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    jid: str = Field(..., min_length=2, max_length=20)
    sev: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    desc: Optional[str] = Field(default="", max_length=500)
    alert_id: Optional[str] = None


class UpdateIncidentStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(OPEN|INVESTIGATING|RESOLVED|CLOSED)$")


class AddIncidentNoteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=300)


class IncidentNoteResponse(BaseModel):
    by: str
    ts: int
    text: str

    model_config = ConfigDict(from_attributes=True)


class IncidentResponse(BaseModel):
    id: str
    title: str
    jid: str
    sev: str
    status: str
    assignee: Optional[str] = None
    desc: str
    ts: int
    notes: List[IncidentNoteResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Alert Schemas
class AlertResponse(BaseModel):
    id: str
    type: str
    sev: str
    jid: Optional[str] = None
    msg: str
    ts: int
    ack: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Sensor Schemas
class RegisterSensorRequest(BaseModel):
    type: str = Field(..., pattern="^(camera|loop|radar)$")
    jid: str = Field(..., min_length=2, max_length=20)
    loc: Optional[str] = Field(default="Approach N", max_length=40)


class SensorResponse(BaseModel):
    id: str
    type: str
    jid: str
    status: str
    lastSeen: Optional[int] = None
    quality: int = 90
    loc: str

    model_config = ConfigDict(from_attributes=True)


class RegisterSensorResponse(BaseModel):
    sensor: SensorResponse
    secret: str


# Audit Schemas (SR-05)
class AuditEntryResponse(BaseModel):
    seq: int
    ts: int
    actor: str
    action: str
    target: str
    result: str
    detail: str
    prev: str
    hash: str

    model_config = ConfigDict(from_attributes=True)


class VerifyAuditResponse(BaseModel):
    ok: bool
    n: Optional[int] = None
    seq: Optional[int] = None


# User Administration Schemas
class SetRoleRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=50)


class SetLockRequest(BaseModel):
    locked: bool


# Telemetry Ingestion Schemas (SR-01 / SR-02)
class TelemetryIngestPayload(BaseModel):
    sensor_id: str = Field(..., min_length=3, max_length=50)
    junction_id: str = Field(..., min_length=2, max_length=20)
    vehicle_count: int = Field(..., ge=0, le=500)
    avg_speed: float = Field(..., ge=0.0, le=250.0)
    occupancy: float = Field(..., ge=0.0, le=1.0)
    timestamp: int  # Milliseconds Unix timestamp
    nonce: str = Field(..., min_length=8, max_length=64)
    signature: str = Field(..., min_length=64, max_length=64)


# Analytics Schemas
class JunctionAnalytics(BaseModel):
    id: str
    name: str
    avg: float
    speed: int
    peak: int
    inc: int


class AnalyticsResponse(BaseModel):
    hours: List[float]
    today: List[Optional[int]]
    perJ: List[JunctionAnalytics]
    sel: List[JunctionAnalytics]
    peak: int
    speed: int
    vehicles: int
