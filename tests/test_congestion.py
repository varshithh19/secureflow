"""Unit tests for Congestion Detection Strategy & Alert Generator (FR-03 / FR-07)."""
from sqlalchemy.orm import Session

from secureflow.models import Alert, Junction
from secureflow.services.congestion import (
    StandardThresholdStrategy,
    check_sensors_health,
    congestion_strategy,
    raise_alert_if_not_deduped,
    update_junction_congestion,
)


def test_standard_threshold_strategy():
    strat = StandardThresholdStrategy()

    # Low (< 0.35)
    assert strat.calculate_level(0.0) == 0
    assert strat.calculate_level(0.34) == 0
    assert strat.get_level_name(0) == "Low"

    # Moderate (0.35 to 0.59)
    assert strat.calculate_level(0.35) == 1
    assert strat.calculate_level(0.59) == 1
    assert strat.get_level_name(1) == "Moderate"

    # High (0.60 to 0.79)
    assert strat.calculate_level(0.60) == 2
    assert strat.calculate_level(0.79) == 2
    assert strat.get_level_name(2) == "High"

    # Severe (>= 0.80)
    assert strat.calculate_level(0.80) == 3
    assert strat.calculate_level(0.99) == 3
    assert strat.get_level_name(3) == "Severe"


def test_critical_congestion_alert_and_deduplication(db_session: Session):
    junction = db_session.get(Junction, "J-01")
    junction.level = 1
    junction.occ = 0.88  # Transition to Severe

    # Update congestion
    update_junction_congestion(db_session, "J-01")

    # Verify CRITICAL alert created
    alerts = db_session.query(Alert).filter(Alert.jid == "J-01", Alert.type == "SEVERE_CONGESTION").all()
    assert len(alerts) >= 1

    # Second immediate trigger should be deduplicated within 5 minutes
    duplicate = raise_alert_if_not_deduped(
        db=db_session,
        alert_type="SEVERE_CONGESTION",
        sev="CRITICAL",
        jid="J-01",
        msg="Central Plaza occupancy is above 80%."
    )
    assert duplicate is None
