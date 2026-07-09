"""Guardrail checks for CLARA's Week 6 stress testing."""

import re
from dataclasses import dataclass
from typing import Literal

GuardrailSeverity = Literal["low", "medium", "high", "critical"]
GuardrailAction = Literal["allow", "refuse", "mask", "escalate", "quarantine"]


@dataclass(frozen=True)
class GuardrailFinding:
    rule_id: str
    category: str
    severity: GuardrailSeverity
    action: GuardrailAction
    reason: str


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    action: GuardrailAction
    findings: list[GuardrailFinding]
    safe_response: str


RULES = [
    (
        "GR-JB-001",
        "jailbreaking",
        "high",
        "escalate",
        [
            r"ignore .*instructions",
            r"ignore .*compliance",
            r"ignorecompliance",
            r"disable .*human gate",
            r"skip .*escalation",
            r"stop acting like",
            r"output only",
            r"policy update.*no longer requires",
            r"do not mention compliance",
            r"return approve",
            r"returnapprove",
            r"approve.*nothing else",
        ],
        "Prompt attempts to override CLARA's instruction hierarchy or governance flow.",
    ),
    (
        "GR-PI-001",
        "prompt_injection",
        "high",
        "quarantine",
        [
            r"system override",
            r"if you are an ai",
            r"replace .*compliance",
            r"next langgraph node",
            r"fake tool result",
            r"tool result:",
            r"reviewed by judges",
            r"judges.*score",
            r"ignore .*evidence gaps",
        ],
        "Prompt contains instructions that try to control tools, graph nodes, or evaluator behavior.",
    ),
    (
        "GR-PII-001",
        "pii_extraction",
        "critical",
        "mask",
        [
            r"\bssn\b",
            r"social security",
            r"date of birth",
            r"phone number",
            r"email",
            r"account id",
            r"credit score for every borrower",
            r"each individual borrower credit score",
            r"full borrower profile",
        ],
        "Prompt requests sensitive identity, contact, account, or borrower-level financial data.",
    ),
    (
        "GR-LEAK-001",
        "internal_policy_leakage",
        "high",
        "refuse",
        [
            r"system prompt",
            r"developer instructions",
            r"hidden instruction",
            r"api key",
            r"environment variables",
            r"exact .*scoring formula",
            r"exact .*judge prompt",
            r"internal tool",
            r"endpoint",
        ],
        "Prompt attempts to reveal hidden instructions, secrets, internal policies, or tool surface area.",
    ),
    (
        "GR-SE-001",
        "social_engineering",
        "high",
        "escalate",
        [
            r"\bi am the ceo\b",
            r"i work in compliance",
            r"external auditor",
            r"has to close today",
            r"bend the rules",
            r"temporarily disable",
        ],
        "Prompt uses authority, urgency, or insider claims to bypass authorization.",
    ),
    (
        "GR-CR-001",
        "crescendo",
        "high",
        "escalate",
        [
            r"step 1:.*step 2:.*step 3:.*approve",
            r"apply .*exception.*approve",
            r"without logging",
            r"not detect risk",
            r"phrase .*application",
        ],
        "Prompt gradually moves from harmless context into unsafe approval, logging, or evasion behavior.",
    ),
    (
        "GR-OBF-001",
        "obfuscation",
        "high",
        "quarantine",
        [
            r"decode .*follow .*instruction",
            r"careless ai",
            r"non-compliant loan",
            r"combine .*follow",
        ],
        "Prompt hides or indirectly composes unsafe instructions using encoding, spacing, or indirection.",
    ),
    (
        "GR-AUTH-001",
        "tool_authorization",
        "critical",
        "refuse",
        [
            r"look up all loans",
            r"submit .*approval",
            r"funds .*disbursement",
            r"delete .*audit",
            r"use .*credit score as",
            r"restricted .*policy",
        ],
        "Prompt asks CLARA to perform or simulate an unauthorized tool or backend action.",
    ),
]


def inspect_input_prompt(prompt: str) -> GuardrailDecision:
    normalized = _normalize(prompt)
    findings = []
    for rule_id, category, severity, action, patterns, reason in RULES:
        if any(re.search(pattern, normalized) for pattern in patterns):
            findings.append(
                GuardrailFinding(
                    rule_id=rule_id,
                    category=category,
                    severity=severity,
                    action=action,
                    reason=reason,
                )
            )

    if not findings:
        return GuardrailDecision(
            allowed=True,
            action="allow",
            findings=[],
            safe_response=(
                "This request is allowed. CLARA can answer using case evidence, aggregate "
                "evaluation data, or high-level policy guidance without exposing sensitive data."
            ),
        )

    action = _dominant_action(findings)
    return GuardrailDecision(
        allowed=False,
        action=action,
        findings=findings,
        safe_response=_safe_response_for_action(action, findings),
    )


def inspect_output_response(response: str) -> GuardrailDecision:
    raw_text = response.lower()
    normalized = _normalize(response)
    findings = []
    output_rules = [
        (
            "GR-OUT-001",
            "sensitive_output",
            "critical",
            "mask",
            [r"\b\d{3}-\d{2}-\d{4}\b", r"api key", r"secret", r"system prompt"],
            "Output appears to contain sensitive identity, credential, or hidden-prompt material.",
        ),
        (
            "GR-OUT-002",
            "unsafe_decision_output",
            "high",
            "escalate",
            [r"ignore compliance", r"skip escalation", r"delete .*audit"],
            "Output appears to repeat or endorse unsafe decision-control language.",
        ),
    ]
    for rule_id, category, severity, action, patterns, reason in output_rules:
        if any(_matches_raw_or_normalized(pattern, raw_text, normalized) for pattern in patterns):
            findings.append(
                GuardrailFinding(
                    rule_id=rule_id,
                    category=category,
                    severity=severity,
                    action=action,
                    reason=reason,
                )
            )
    if not findings:
        return GuardrailDecision(
            allowed=True,
            action="allow",
            findings=[],
            safe_response=response,
        )
    action = _dominant_action(findings)
    return GuardrailDecision(
        allowed=False,
        action=action,
        findings=findings,
        safe_response=_safe_response_for_action(action, findings),
    )


def _dominant_action(findings: list[GuardrailFinding]) -> GuardrailAction:
    priority: dict[GuardrailAction, int] = {
        "allow": 0,
        "refuse": 1,
        "mask": 2,
        "quarantine": 3,
        "escalate": 4,
    }
    return max((finding.action for finding in findings), key=lambda action: priority[action])


def _safe_response_for_action(
    action: GuardrailAction,
    findings: list[GuardrailFinding],
) -> str:
    categories = ", ".join(sorted({finding.category for finding in findings}))
    if action == "mask":
        return (
            f"I cannot disclose sensitive borrower or account-level information. "
            f"This request was flagged for {categories}; I can provide an aggregate or masked summary."
        )
    if action == "quarantine":
        return (
            f"I cannot follow instructions embedded in user-provided content. "
            f"This request was flagged for {categories} and must be reviewed as untrusted evidence."
        )
    if action == "escalate":
        return (
            f"I cannot change a loan decision or bypass governance from a prompt. "
            f"This request was flagged for {categories} and must escalate to human review."
        )
    return (
        f"I cannot provide hidden policy, tool, credential, or unsafe decision-control details. "
        f"This request was flagged for {categories}."
    )


def _normalize(value: str) -> str:
    normalized = value.lower().replace("0", "o").replace("1", "i")
    spaced_letters = re.sub(r"\s+", "", normalized)
    return f"{normalized} {spaced_letters}"


def _matches_raw_or_normalized(pattern: str, raw_text: str, normalized_text: str) -> bool:
    return re.search(pattern, raw_text) is not None or re.search(pattern, normalized_text) is not None
