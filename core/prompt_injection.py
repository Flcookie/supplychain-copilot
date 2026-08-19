"""Prompt-injection detection and output sanitization for Policy QA / RAG paths.

Defense-in-depth:
1. Input pattern scan (instruction override / role hijack / data exfil)
2. Hardened system prompt rules (see POLICY_QA_PROMPT)
3. Retrieved-document isolation: wrap as untrusted + drop instruction-hijack chunks
4. Output-side sensitive-field filter as last resort
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["high", "medium", "low"]
AttackType = Literal[
    "instruction_override",
    "role_hijack",
    "data_exfil",
    "jailbreak",
    "system_prompt_leak",
]


@dataclass(frozen=True)
class InjectionHit:
    attack_type: AttackType
    severity: Severity
    pattern: str
    matched_text: str


@dataclass(frozen=True)
class InjectionScanResult:
    is_injection: bool
    should_refuse: bool
    hits: tuple[InjectionHit, ...]
    reasons: tuple[str, ...]

    @property
    def primary_attack(self) -> AttackType | None:
        return self.hits[0].attack_type if self.hits else None


# (compiled pattern, attack_type, severity, reason)
_INJECTION_RULES: list[tuple[re.Pattern[str], AttackType, Severity, str]] = [
    (
        re.compile(
            r"ignore\s+(all\s+)?(previous|above|prior|the)\s+(instructions?|prompts?|rules?|context)",
            re.I,
        ),
        "instruction_override",
        "high",
        "Instruction-override attempt (EN)",
    ),
    (
        re.compile(r"disregard\s+(your|the|all)\s+(system|safety|previous|above)", re.I),
        "instruction_override",
        "high",
        "Disregard-system attempt (EN)",
    ),
    (
        re.compile(r"忽略.{0,10}(上述|之前|以上|先前|系统).{0,10}(指令|规则|提示|设定)"),
        "instruction_override",
        "high",
        "Instruction-override attempt (ZH)",
    ),
    (
        re.compile(r"(不要|别|无需).{0,6}(遵守|遵循|理会).{0,8}(规则|指令|提示)"),
        "instruction_override",
        "high",
        "Ignore-rules attempt (ZH)",
    ),
    (
        re.compile(
            r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\s+"
            r"(dan|unrestricted|admin|administrator|developer|root|jailbreak)",
            re.I,
        ),
        "role_hijack",
        "high",
        "Role-hijack attempt (EN)",
    ),
    (
        re.compile(r"扮演.{0,10}(管理员|系统|开发者|超级用户|root)"),
        "role_hijack",
        "high",
        "Role-hijack attempt (ZH)",
    ),
    (
        re.compile(r"\bjailbreak\b", re.I),
        "jailbreak",
        "high",
        "Explicit jailbreak keyword",
    ),
    (
        re.compile(
            r"(reveal|show|print|dump|output)\s+(your\s+|the\s+)?(system\s+prompt|hidden\s+instructions?)",
            re.I,
        ),
        "system_prompt_leak",
        "high",
        "System-prompt leak attempt",
    ),
    (
        re.compile(r"(?i)\bsudo\s+mode\b"),
        "role_hijack",
        "high",
        "Elevated sudo-mode request",
    ),
    (
        re.compile(r"(输出|打印|展示).{0,8}(系统提示|系统指令|隐藏指令|原始prompt)", re.I),
        "system_prompt_leak",
        "high",
        "System-prompt leak attempt (ZH)",
    ),
    (
        re.compile(
            r"(output|dump|export|list|show)\s+(all|every|entire)\s+"
            r"(supplier|contract|confidential|internal|pricing|amount)",
            re.I,
        ),
        "data_exfil",
        "high",
        "Broad data-exfiltration attempt (EN)",
    ),
    (
        re.compile(r"输出所有.{0,16}(合同|金额|供应商|机密|内部|定价|单价)"),
        "data_exfil",
        "high",
        "Broad data-exfiltration attempt (ZH)",
    ),
    (
        re.compile(
            r"(bypass|override)\s+(safety|security|policy|guardrail|filter)",
            re.I,
        ),
        "instruction_override",
        "medium",
        "Safety-bypass language",
    ),
    (
        re.compile(r"(developer\s+mode|sudo\s+mode|god\s+mode)", re.I),
        "role_hijack",
        "medium",
        "Elevated-mode request",
    ),
]

_SENSITIVE_OUTPUT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)contract\s+amount[s]?\s*[:=]\s*[\d,$€¥.]+"),
    re.compile(r"(?i)unit\s+price[s]?\s*[:=]\s*[\d,$€¥.]+"),
    re.compile(r"合同金额\s*[：:=]\s*[\d,.$€¥万千百]+"),
    re.compile(r"单价\s*[：:=]\s*[\d,.$€¥万千百]+"),
    re.compile(r"(?i)confidential\s+(pricing|salary|bank|account)"),
    re.compile(r"机密.{0,6}(定价|薪资|账号|账户)"),
]


_REFUSAL_EN = (
    "I can't follow instructions that try to override my system role or exfiltrate "
    "restricted supplier/contract data. Ask a specific policy question instead "
    "(e.g. qualification steps, ESG scoring rules, or review cadence)."
)

_REFUSAL_ZH = (
    "无法执行试图覆盖系统角色、或批量导出受限供应商/合同数据的指令。"
    "请改问具体政策问题（例如准入步骤、ESG 计分规则、或复审周期）。"
)

_POISONED_CONTEXT_EN = (
    "Retrieved policy documents contained instruction-like content and were excluded. "
    "I cannot answer from poisoned context. Re-ask a specific policy question, "
    "or verify the document corpus."
)

_POISONED_CONTEXT_ZH = (
    "检索到的政策文档含有指令式内容，已全部排除，无法基于被污染的上下文作答。"
    "请改问具体政策问题，或检查文档语料是否被篡改。"
)

# Indirect injection = instruction hijack hidden in retrieved text.
# Do NOT drop data_exfil-only language: real policies often say "do not export all amounts".
_INDIRECT_ATTACK_TYPES = frozenset(
    {"instruction_override", "role_hijack", "jailbreak", "system_prompt_leak"}
)


def scan_user_input(text: str) -> InjectionScanResult:
    """Scan user text for common prompt-injection / jailbreak patterns."""
    raw = text or ""
    hits: list[InjectionHit] = []
    for pattern, attack_type, severity, reason in _INJECTION_RULES:
        match = pattern.search(raw)
        if not match:
            continue
        hits.append(
            InjectionHit(
                attack_type=attack_type,
                severity=severity,
                pattern=pattern.pattern,
                matched_text=match.group(0)[:120],
            )
        )
    # Deduplicate by attack_type keeping highest severity
    severity_rank = {"high": 3, "medium": 2, "low": 1}
    best: dict[AttackType, InjectionHit] = {}
    for hit in hits:
        prev = best.get(hit.attack_type)
        if prev is None or severity_rank[hit.severity] > severity_rank[prev.severity]:
            best[hit.attack_type] = hit
    ordered = tuple(
        sorted(best.values(), key=lambda h: severity_rank[h.severity], reverse=True)
    )
    should_refuse = any(h.severity == "high" for h in ordered)
    reasons = tuple(
        f"{h.attack_type}:{h.matched_text}" for h in ordered
    )
    # Also attach human-readable reasons from rules via matched attack types
    _ = reasons
    return InjectionScanResult(
        is_injection=bool(ordered),
        should_refuse=should_refuse,
        hits=ordered,
        reasons=tuple(
            next(
                (
                    rule_reason
                    for pat, atype, sev, rule_reason in _INJECTION_RULES
                    if atype == h.attack_type and sev == h.severity
                ),
                h.attack_type,
            )
            for h in ordered
        ),
    )


def refusal_message(lang: str | None = "en") -> str:
    return _REFUSAL_ZH if (lang or "en").lower().startswith("zh") else _REFUSAL_EN


def sanitize_answer(answer: str) -> tuple[str, list[str]]:
    """Strip obvious sensitive field dumps from model output. Returns (text, redactions)."""
    text = answer or ""
    redactions: list[str] = []
    for pattern in _SENSITIVE_OUTPUT_PATTERNS:
        if pattern.search(text):
            redactions.append(pattern.pattern)
            text = pattern.sub("[REDACTED_SENSITIVE_FIELD]", text)
    return text, redactions


def wrap_question_for_prompt(question: str) -> str:
    """Mark user text as untrusted data so the model treats directive language as content."""
    return (
        "<<<USER_QUESTION_UNTRUSTED>>>\n"
        f"{question}\n"
        "<<<END_USER_QUESTION_UNTRUSTED>>>"
    )


def wrap_retrieved_context(context: str) -> str:
    """Mark retrieved chunks as untrusted data, never as executable instructions."""
    body = (context or "").strip() or "(no retrieved documents)"
    return (
        "<<<RETRIEVED_DOCUMENT_UNTRUSTED>>>\n"
        f"{body}\n"
        "<<<END_RETRIEVED_DOCUMENT_UNTRUSTED>>>"
    )


def doc_text(doc: Any) -> str:
    if hasattr(doc, "page_content"):
        return getattr(doc, "page_content") or ""
    if isinstance(doc, dict):
        return doc.get("content") or doc.get("page_content") or ""
    return str(doc or "")


def is_indirect_injection(text: str) -> bool:
    """True when retrieved text tries to hijack the model (not ordinary dump wording)."""
    scan = scan_user_input(text)
    return any(
        hit.severity == "high" and hit.attack_type in _INDIRECT_ATTACK_TYPES for hit in scan.hits
    )


def split_poisoned_docs(docs: list[Any]) -> tuple[list[Any], list[Any]]:
    """Keep evidence chunks; drop those that look like instruction hijacks."""
    kept: list[Any] = []
    dropped: list[Any] = []
    for doc in docs or []:
        if is_indirect_injection(doc_text(doc)):
            dropped.append(doc)
        else:
            kept.append(doc)
    return kept, dropped


def prepare_retrieved_context(docs: list[Any]) -> dict[str, Any]:
    """Filter poisoned chunks and wrap the remainder for the generator prompt."""
    kept, dropped = split_poisoned_docs(docs)
    joined = "\n\n".join(doc_text(doc) for doc in kept)
    limitations: list[str] = []
    if dropped:
        limitations.append(
            f"Dropped {len(dropped)} retrieved chunk(s) that contained instruction-like injection."
        )
    return {
        "kept": kept,
        "dropped": dropped,
        "context": wrap_retrieved_context(joined),
        "all_poisoned": bool(docs) and not kept,
        "limitations": limitations,
    }


def poisoned_context_refusal(lang: str | None = "en") -> str:
    return _POISONED_CONTEXT_ZH if (lang or "en").lower().startswith("zh") else _POISONED_CONTEXT_EN
