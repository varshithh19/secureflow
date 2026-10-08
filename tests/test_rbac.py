"""Unit tests for Server-Side RBAC Enforcement (SR-03 / PERMS Matrix)."""
import pytest
from fastapi import HTTPException
from secureflow.core.constants import PERMS
from secureflow.core.rbac import AuthenticatedUser


def test_authenticated_user_permissions():
    operator = AuthenticatedUser(user_id="priya", role="operator")
    supervisor = AuthenticatedUser(user_id="meera", role="supervisor")
    admin = AuthenticatedUser(user_id="sana", role="admin")
    analyst = AuthenticatedUser(user_id="dev", role="analyst")
    auditor = AuthenticatedUser(user_id="kavya", role="auditor")
    dispatcher = AuthenticatedUser(user_id="ems", role="emergency_dispatcher")

    # dashboard.view
    assert operator.has_permission("dashboard.view") is True
    assert auditor.has_permission("dashboard.view") is True

    # signal.propose
    assert operator.has_permission("signal.propose") is True
    assert supervisor.has_permission("signal.propose") is True
    assert admin.has_permission("signal.propose") is False
    assert analyst.has_permission("signal.propose") is False

    # signal.approve (supervisor only)
    assert supervisor.has_permission("signal.approve") is True
    assert operator.has_permission("signal.approve") is False
    assert admin.has_permission("signal.approve") is False

    # emergency.create
    assert dispatcher.has_permission("emergency.create") is True
    assert operator.has_permission("emergency.create") is False
    assert supervisor.has_permission("emergency.create") is False

    # emergency.cancel
    assert dispatcher.has_permission("emergency.cancel") is True
    assert supervisor.has_permission("emergency.cancel") is True
    assert operator.has_permission("emergency.cancel") is False

    # user.manage & sensor.manage (admin only)
    assert admin.has_permission("user.manage") is True
    assert admin.has_permission("sensor.manage") is True
    assert supervisor.has_permission("user.manage") is False
    assert operator.has_permission("sensor.manage") is False

    # audit.view
    assert admin.has_permission("audit.view") is True
    assert auditor.has_permission("audit.view") is True
    assert operator.has_permission("audit.view") is False


def test_deny_by_default_on_unknown_permission():
    user = AuthenticatedUser(user_id="sana", role="admin")
    assert user.has_permission("unknown.action") is False
    assert user.has_permission("root.execute") is False
