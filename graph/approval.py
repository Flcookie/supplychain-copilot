"""One-shot HITL gate: interrupt, wait for buyer approve/reject, never write the DB."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from .state import SCState

# Status / recommendation strings that must not auto-apply.
_GATED_STATUS_FRAGMENTS = (
    "qualified with reserve",
    "disqualified",
    "blacklist",
    "blacklisted",
    "under review",
    "phase-out",
    "phase out",
    "blocked",
)
_GATED_ACTION_FRAGMENTS = (
    "blacklist",
    "phase-out",
    "phase out",
    "disqualif",
    "reserve",
    "exit",
    "block",
    "replace",
)


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and value != 0:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "y", "true", "1", "required"}
    return False


def _first_profile_row(state: SCState) -> dict[str, Any]:
    profile = state.get("assessment_profile") or {}
    rows = profile.get("rows") if isinstance(profile, dict) else None
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return rows[0]
    return {}


def infer_proposed_action(state: SCState) -> dict[str, Any]:
    """Decide whether this turn proposes a gated supplier action.

    Gated means: blacklist, status change, phase-out, or a risk event that
    already requires human review. The agent never writes those itself.
    """
    reasons: list[str] = []
    action = "none"

    if state.get("human_approval_required"):
        reasons.append("router_or_specialist_flagged_hitl")
        action = "gated_recommendation"

    row = _first_profile_row(state)
    status = str(row.get("qualification_status") or "")
    rating = str(row.get("rating_class") or "").strip().upper()
    suggested = str(row.get("suggested_action") or "")
    risk_level = str(row.get("risk_level") or "")

    status_l = status.lower()
    if any(frag in status_l for frag in _GATED_STATUS_FRAGMENTS):
        reasons.append(f"qualification_status={status}")
        action = "status_change"

    if rating in {"C", "D"}:
        reasons.append(f"rating_class={rating}")
        if action == "none":
            action = "status_change"

    suggested_l = suggested.lower()
    if any(frag in suggested_l for frag in _GATED_ACTION_FRAGMENTS):
        reasons.append(f"suggested_action={suggested}")
        action = "status_change"

    risk_block = state.get("assessment_risk") or {}
    risk_rows = risk_block.get("rows") if isinstance(risk_block, dict) else None
    if isinstance(risk_rows, list):
        for risk in risk_rows:
            if not isinstance(risk, dict):
                continue
            if _truthy(risk.get("human_review_required")):
                rid = risk.get("risk_event_id") or "unknown"
                reasons.append(f"risk_event={rid} human_review_required")
                if action == "none":
                    action = "human_review"
            rec = str(risk.get("recommended_action") or "").lower()
            if "blacklist" in rec or "黑名单" in rec:
                reasons.append("risk_recommended_blacklist")
                action = "blacklist"

    question = state.get("question") or ""
    q_l = question.lower()
    if "blacklist" in q_l or "黑名单" in question:
        reasons.append("question_requests_blacklist")
        action = "blacklist"

    scenario = state.get("scenario_spec") or {}
    if isinstance(scenario, dict) and (
        scenario.get("human_approval_required") or scenario.get("risk_type") == "blacklist"
    ):
        reasons.append("scenario_blacklist_or_hitl")
        action = "blacklist"

    return {
        "action": action,
        "reasons": reasons,
        "gated": bool(reasons) and action != "none",
        "supplier_id": state.get("supplier_id"),
        "qualification_status": status or None,
        "rating_class": rating or None,
        "risk_level": risk_level or None,
        "writes_database": False,
    }


def needs_hitl(state: SCState) -> bool:
    if state.get("injection_blocked") or state.get("ambiguity_type"):
        return False
    if state.get("approval_decision") in {"approved", "rejected"}:
        return False
    return infer_proposed_action(state)["gated"]


def build_interrupt_payload(state: SCState) -> dict[str, Any]:
    proposed = infer_proposed_action(state)
    zh = state.get("response_language", "en") == "zh"
    sid = state.get("supplier_id") or "unknown"
    if zh:
        message = (
            f"评估已暂停，等待采购确认（供应商 {sid}）。"
            "批准后仅保留建议，不会写入供应商主数据；驳回则搁置该建议。"
        )
    else:
        message = (
            f"Assessment paused for buyer confirmation ({sid}). "
            "Approve keeps the recommendation; reject parks it. "
            "The agent never writes supplier master data."
        )
    answer = state.get("answer") or ""
    return {
        "kind": "human_approval",
        "supplier_id": state.get("supplier_id"),
        "proposed_action": proposed["action"],
        "reasons": proposed["reasons"],
        "writes_database": False,
        "message": message,
        "draft_preview": answer[:500],
        "review_status": state.get("review_status"),
        "task_type": state.get("task_type"),
        "thread_id": state.get("thread_id"),
    }


def _normalize_decision(value: Any) -> tuple[bool, str]:
    if value is True:
        return True, ""
    if value is False:
        return False, ""
    if isinstance(value, str):
        token = value.strip().lower()
        return token in {"approve", "approved", "yes", "true", "ok", "1"}, value.strip()
    if isinstance(value, dict):
        raw = value.get("approved", False)
        if isinstance(raw, str):
            approved = raw.strip().lower() in {"true", "yes", "approve", "approved", "1"}
        else:
            approved = bool(raw)
        note = str(value.get("note") or "").strip()
        return approved, note
    return False, str(value)


def _stamp(approved: bool, note: str, *, zh: bool) -> str:
    extra = f" Note: {note}" if note and not zh else (f" 备注：{note}" if note else "")
    if zh:
        if approved:
            return (
                "\n\n---\n**人工批准：** 采购已确认本条建议。"
                "系统未改供应商状态或黑名单（只读演示库）。"
                f"{extra}"
            )
        return (
            "\n\n---\n**人工驳回：** 采购未批准，建议已搁置。"
            "未写入任何状态变更。"
            f"{extra}"
        )
    if approved:
        return (
            "\n\n---\n**Human approval:** Buyer confirmed this recommendation. "
            "No supplier status or blacklist was written (read-only demo DB)."
            f"{extra}"
        )
    return (
        "\n\n---\n**Human rejection:** Buyer declined; the recommendation is parked. "
        "No status change was written."
        f"{extra}"
    )


def approval_node(state: SCState) -> SCState:
    """Pause here until Command(resume=...) arrives. Re-runs from the top on resume."""
    payload = build_interrupt_payload(state)
    decision = interrupt(payload)
    approved, note = _normalize_decision(decision)
    zh = state.get("response_language", "en") == "zh"
    stamp = _stamp(approved, note, zh=zh)
    answer = (state.get("answer") or "").rstrip()
    if stamp.strip() not in answer:
        answer = answer + stamp
    return {
        "approval_decision": "approved" if approved else "rejected",
        "approval_note": note,
        "human_approval_required": True,
        "proposed_action": payload["proposed_action"],
        "proposed_action_reasons": payload["reasons"],
        "task_step": "approval_resolved",
        "answer": answer,
    }
