"""Unit tests for Signal Interval Bounds & SAFE Constants Validation (SR-04)."""
from secureflow.services.signals import validate_timing_plan


def test_valid_signal_plans():
    valid_plan = {"ns": 45, "ew": 40, "yellow": 3, "allred": 2}
    assert validate_timing_plan(valid_plan) is None

    boundary_min = {"ns": 10, "ew": 10, "yellow": 3, "allred": 1}
    assert validate_timing_plan(boundary_min) is None

    boundary_max = {"ns": 100, "ew": 100, "yellow": 5, "allred": 5}
    assert validate_timing_plan(boundary_max) is None


def test_invalid_signal_intervals():
    # NS too short (< 10s)
    plan_short_ns = {"ns": 5, "ew": 40, "yellow": 3, "allred": 2}
    err1 = validate_timing_plan(plan_short_ns)
    assert err1 is not None
    assert "North-south green must be a whole number from 10 to 120" in err1

    # EW too long (> 120s)
    plan_long_ew = {"ns": 45, "ew": 130, "yellow": 3, "allred": 2}
    err2 = validate_timing_plan(plan_long_ew)
    assert err2 is not None
    assert "East-west green must be a whole number from 10 to 120" in err2

    # Amber invalid
    plan_bad_yellow = {"ns": 45, "ew": 40, "yellow": 2, "allred": 2}
    assert "Amber must be a whole number from 3 to 5" in validate_timing_plan(plan_bad_yellow)

    # All-red invalid
    plan_bad_allred = {"ns": 45, "ew": 40, "yellow": 3, "allred": 6}
    assert "All-red must be a whole number from 1 to 5" in validate_timing_plan(plan_bad_allred)


def test_cycle_length_limit():
    # ns: 120, ew: 120, yellow: 5, allred: 5 -> cycle = 120 + 120 + 2*(10) = 260s (> 240 limit)
    over_cycle = {"ns": 120, "ew": 120, "yellow": 5, "allred": 5}
    err = validate_timing_plan(over_cycle)
    assert err is not None
    assert "Cycle length 260 s is above the 240 s limit" in err
