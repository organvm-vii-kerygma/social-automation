"""Fixture-backed policy and receipt tests for the LinkedIn effector."""

from kerygma_social.delivery_log import DeliveryLog
from kerygma_social.linkedin import LinkedInAction, send_linkedin_action


def _action(**overrides):
    values = {
        "account": "professional",
        "profile_id": "profile-123",
        "action": "follow-up",
        "obligation_id": "obligation-1",
        "context_path": "/private/browser-context",
        "run_id": "run-1",
    }
    values.update(overrides)
    return LinkedInAction(**values)


class Browser:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def execute(self, *, action, context_path):
        self.calls += 1
        assert context_path == action.context_path
        return self.response


def test_disarmed_action_never_calls_browser():
    browser = Browser({"success": True, "provider_id": "m1"})
    receipt = send_linkedin_action(_action(), browser, fire=False)
    assert receipt["state"] == "prepared"
    assert browser.calls == 0


def test_exact_provider_receipt_is_confirmed_and_deduplicated():
    browser = Browser({"success": True, "provider_id": "m1", "profile_id": "profile-123"})
    log = DeliveryLog()
    first = send_linkedin_action(_action(), browser, fire=True, delivery_log=log)
    second = send_linkedin_action(_action(), browser, fire=True, delivery_log=log)
    assert first["state"] == "confirmed"
    assert first["confirmation_evidence"] == ["linkedin:provider:m1"]
    assert second["state"] == "confirmed"
    assert browser.calls == 1


def test_missing_provider_id_is_attempted_and_retry_locked():
    receipt = send_linkedin_action(
        _action(), Browser({"success": True, "profile_id": "profile-123"}), fire=True
    )
    assert receipt["state"] == "attempted"
    assert receipt["retry_locked"] is True
    assert receipt["failure_category"] == "confirmation_missing"


def test_provider_safety_conditions_and_personal_approval():
    browser = Browser({"success": True, "provider_id": "m1", "profile_id": "profile-123"})
    assert (
        send_linkedin_action(_action(), None, fire=True)["failure_category"]
        == "browser_adapter_unavailable"
    )
    assert (
        send_linkedin_action(_action(action="personal_message"), browser, fire=True)[
            "failure_category"
        ]
        == "approval_required"
    )
    assert (
        send_linkedin_action(
            _action(action="connection"),
            Browser({"captcha": True}),
            fire=True,
        )["failure_category"]
        == "captcha_required"
    )
    assert (
        send_linkedin_action(
            _action(action="connection"),
            Browser({"profile_found": False}),
            fire=True,
        )["failure_category"]
        == "ambiguous_identity"
    )
