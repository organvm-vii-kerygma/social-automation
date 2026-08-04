"""Receipt-backed LinkedIn actions using a runtime-supplied browser adapter.

This module deliberately does not own a browser session or credentials. The
caller supplies a private persistent-context handle and an adapter with an
``execute`` method. The module owns policy, exact-target deduplication, and
redacted delivery receipts.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from .delivery_log import DeliveryLog, DeliveryRecord

PROFESSIONAL_ACTIONS = {
    "application",
    "connection",
    "follow-up",
    "followup",
    "recruiter_followup",
    "professional_message",
}
APPROVAL_ACTIONS = {"personal_message", "profile_edit"}
BLOCKED_ERRORS = {
    "auth_lost": "authentication_lost",
    "stale_page": "stale_page",
    "captcha": "captcha_required",
    "missing_target": "target_not_found",
    "ambiguous_identity": "ambiguous_identity",
}


def _stable_id(*values: object) -> str:
    material = "\x1f".join(str(value) for value in values).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:32]


@dataclass(frozen=True)
class LinkedInAction:
    """A target-bound action; message bodies remain outside this object."""

    account: str
    profile_id: str
    action: str
    obligation_id: str
    context_path: str
    run_id: str = ""
    audience: str = "professional"
    approved: bool = False
    content_hash: str = ""
    attachment_hashes: list[str] = field(default_factory=list)

    @property
    def dedup_key(self) -> str:
        return _stable_id(
            "linkedin-action-v1",
            self.account,
            self.profile_id,
            self.action,
            self.obligation_id,
        )


class LinkedInBrowser(Protocol):
    """Runtime-owned browser adapter contract."""

    def execute(self, *, action: LinkedInAction, context_path: str) -> Mapping[str, Any]: ...


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _receipt(
    action: LinkedInAction,
    *,
    state: str,
    provider_response: Mapping[str, Any] | str = "",
    evidence: list[str] | None = None,
    failure_category: str | None = None,
    retry_locked: bool = False,
) -> dict[str, Any]:
    return {
        "schema": "limen.delivery_receipt.v1",
        "receipt_id": f"linkedin:{action.dedup_key}",
        "exact_target": action.profile_id,
        "attempted_action": action.action,
        "provider": "linkedin",
        "account": action.account,
        "run_id": action.run_id,
        "obligation_id": action.obligation_id,
        "provider_response": provider_response,
        "timestamp": _now(),
        "confirmation_evidence": evidence or [],
        "failure_category": failure_category,
        "state": state,
        "retry_locked": retry_locked,
    }


def _blocked(action: LinkedInAction, category: str, response: str = "") -> dict[str, Any]:
    return _receipt(
        action,
        state="blocked",
        provider_response=response or category,
        failure_category=category,
    )


def _safe_response(value: Mapping[str, Any]) -> dict[str, Any]:
    """Keep provider diagnostics bounded and free of message bodies."""
    safe: dict[str, Any] = {}
    for key in ("state", "status", "provider_id", "profile_id", "error_code", "page"):
        item = value.get(key)
        if isinstance(item, (str, int, float, bool)):
            safe[key] = item
    return safe


def _log_receipt(log: DeliveryLog, action: LinkedInAction, receipt: Mapping[str, Any]) -> None:
    state = str(receipt.get("state", "blocked"))
    log.append(
        DeliveryRecord(
            record_id=str(receipt["receipt_id"]),
            post_id=action.dedup_key,
            platform="linkedin",
            status="success" if state == "confirmed" else "failure",
            external_url=action.profile_id,
            error=str(receipt.get("failure_category") or ""),
            metadata={
                "account": action.account,
                "profile_id": action.profile_id,
                "action": action.action,
                "obligation_id": action.obligation_id,
                "state": state,
                "provider_id": (receipt.get("provider_response") or {}).get("provider_id", "")
                if isinstance(receipt.get("provider_response"), dict)
                else "",
            },
        )
    )


def _existing_receipt(log: DeliveryLog, action: LinkedInAction) -> dict[str, Any] | None:
    for record in log.all_records:
        if (
            record.platform == "linkedin"
            and record.status == "success"
            and record.metadata.get("account") == action.account
            and record.metadata.get("profile_id") == action.profile_id
            and record.metadata.get("action") == action.action
            and record.metadata.get("obligation_id") == action.obligation_id
        ):
            provider_id = str(record.metadata.get("provider_id") or "")
            return _receipt(
                action,
                state="confirmed",
                provider_response={"provider_id": provider_id} if provider_id else "delivery log",
                evidence=[f"linkedin:provider:{provider_id}"]
                if provider_id
                else ["delivery-log:linkedin"],
            )
    return None


def send_linkedin_action(
    action: LinkedInAction,
    browser: LinkedInBrowser | Any | None = None,
    *,
    fire: bool = False,
    delivery_log: DeliveryLog | None = None,
) -> dict[str, Any]:
    """Prepare or execute one professional LinkedIn action.

    ``fire`` is invocation-scoped. No browser call occurs unless it is true,
    the action is professional (or explicitly approved), and a private context
    handle plus runtime adapter are present.
    """
    log = delivery_log or DeliveryLog()
    action_name = action.action.strip().lower()
    if (
        not action.account.strip()
        or not action.profile_id.strip()
        or not action.obligation_id.strip()
    ):
        return _blocked(action, "missing_exact_target")
    if action_name in APPROVAL_ACTIONS and not action.approved:
        return _blocked(action, "approval_required")
    if action_name not in PROFESSIONAL_ACTIONS and action_name not in APPROVAL_ACTIONS:
        return _blocked(action, "unsupported_or_personal_action")
    if action.audience.lower() != "professional" and not action.approved:
        return _blocked(action, "approval_required")
    if not action.context_path.strip():
        return _blocked(action, "browser_context_unavailable")
    if not fire:
        return _receipt(action, state="prepared", provider_response="fire disarmed")
    if browser is None:
        return _blocked(action, "browser_adapter_unavailable")

    existing = _existing_receipt(log, action)
    if existing:
        return existing

    try:
        if callable(browser):
            response = browser(action=action, context_path=action.context_path)
        else:
            response = browser.execute(action=action, context_path=action.context_path)
    except Exception as exc:  # adapter owns provider-specific exception classes
        receipt = _blocked(action, "browser_execution_error", type(exc).__name__)
        _log_receipt(log, action, receipt)
        return receipt

    if not isinstance(response, Mapping):
        receipt = _blocked(action, "invalid_provider_response")
        _log_receipt(log, action, receipt)
        return receipt
    for key, category in BLOCKED_ERRORS.items():
        if response.get(key) is True or str(response.get("error_category", "")).lower() == key:
            receipt = _blocked(action, category, str(response.get("error_code") or key))
            _log_receipt(log, action, receipt)
            return receipt
    returned_profile = str(response.get("profile_id") or "")
    if response.get("profile_found") is False or (
        returned_profile and returned_profile != action.profile_id
    ):
        receipt = _blocked(action, "ambiguous_identity")
        _log_receipt(log, action, receipt)
        return receipt

    provider_id = str(response.get("provider_id") or response.get("message_id") or "")
    successful = bool(
        response.get("confirmed") or response.get("delivered") or response.get("success")
    )
    if successful and provider_id:
        receipt = _receipt(
            action,
            state="confirmed",
            provider_response=_safe_response(response),
            evidence=[f"linkedin:provider:{provider_id}"],
        )
    elif successful:
        receipt = _receipt(
            action,
            state="attempted",
            provider_response=_safe_response(response),
            failure_category="confirmation_missing",
            retry_locked=True,
        )
    else:
        receipt = _blocked(
            action,
            str(response.get("failure_category") or "provider_rejected"),
            str(response.get("error_code") or "provider rejected action"),
        )
    _log_receipt(log, action, receipt)
    return receipt
