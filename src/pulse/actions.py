"""Rule-based action ideas grounded in Groww theme vocabulary (Phase 3)."""

from __future__ import annotations

# Concrete product levers — keyed by theme_id (not generic UX filler).
_ACTION_BY_THEME: dict[str, str] = {
    "kyc": (
        "Improve selfie / eSign / DigiLocker failure recovery and keep KYC status "
        "parity between web and mobile"
    ),
    "withdrawals": (
        "Surface clearer pending/rejected withdrawal reasons (including IFSC) "
        "and an in-app settlement SLA status"
    ),
    "trading": (
        "Explain order cancel/pending outcomes in-app and harden chart / F&O "
        "stability during market hours"
    ),
    "payments": (
        "Fix UPI mandate and add-money redirect loops, then refresh balance "
        "immediately after bank success"
    ),
    "onboarding": (
        "Stop duplicate document asks during signup and fix OTP delivery / resend "
        "so account opening is not blocked"
    ),
    "support": (
        "Route theme-specific failures to guided help with ticket status instead "
        "of generic chat dead-ends"
    ),
    "stability": (
        "Prioritize crash/freeze fixes on option chain and chart screens for "
        "mid-range Android devices"
    ),
    "general": (
        "Triage remaining general feedback into the nearest product theme before "
        "scheduling work"
    ),
}


def action_for_theme(theme_id: str, label: str) -> str:
    """Return one concrete action string for a theme."""
    base = _ACTION_BY_THEME.get(theme_id)
    if base:
        return base
    # Merged labels may keep a known id; fall back on keyword hints in the label.
    lower = label.lower()
    for key, action in _ACTION_BY_THEME.items():
        if key != "general" and key in lower:
            return action
    return (
        f"Investigate top complaints under “{label}” and ship a measurable fix "
        "tied to the quoted pain"
    )
