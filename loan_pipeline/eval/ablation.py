"""Ablation study runner for the loan review pipeline."""

import json
from typing import Callable

from loan_pipeline.agents.compliance_checker import run_compliance_checker
from loan_pipeline.agents.credit_risk_scorer import run_credit_risk_scorer
from loan_pipeline.agents.term_extractor import extract_terms
from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.metrics import CaseScore, GoldLabel, score_case, summarize_scores
from loan_pipeline.eval.run_eval import load_gold_labels
from loan_pipeline.graph.orchestrator import run_pipeline, synthesize_review_packet
from loan_pipeline.graph.state import ComplianceResult, ExtractedTerms, LoanCase, ReviewPacket, RiskResult

AblationRunner = Callable[[LoanCase], ReviewPacket]


def run_ablation_study() -> dict[str, object]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    labels = load_gold_labels()

    configs: dict[str, AblationRunner] = {
        "full_pipeline": run_pipeline,
        "no_compliance_checker": run_without_compliance_checker,
        "no_risk_scorer": run_without_risk_scorer,
        "term_extractor_only": run_term_extractor_only,
        "single_agent_baseline_stub": run_single_agent_baseline_stub,
    }

    results = {}
    for config_name, runner in configs.items():
        scores: list[CaseScore] = []
        for label in labels:
            loan_case = cases[label.case_id]
            packet = runner(loan_case)
            scores.append(score_case(loan_case, packet, label))

        results[config_name] = summarize_scores(scores)["overall"]

    return results


def run_without_compliance_checker(loan_case: LoanCase) -> ReviewPacket:
    terms = extract_terms(loan_case)
    risk = run_credit_risk_scorer(terms)
    compliance = ComplianceResult(status="PASS", findings=[], confidence=0.20)
    return synthesize_review_packet(
        terms=terms,
        compliance=compliance,
        risk=risk,
        validation_errors=[],
    )


def run_without_risk_scorer(loan_case: LoanCase) -> ReviewPacket:
    terms = extract_terms(loan_case)
    compliance = run_compliance_checker(terms)
    risk = RiskResult(
        score=1,
        band="LOW",
        confidence=0.20,
        primary_risk_factors=[],
        mitigating_factors=["Risk scorer disabled; defaulting to low risk."],
        rationale="Ablation run disabled the credit risk scorer.",
    )
    return synthesize_review_packet(
        terms=terms,
        compliance=compliance,
        risk=risk,
        validation_errors=[],
    )


def run_term_extractor_only(loan_case: LoanCase) -> ReviewPacket:
    terms = extract_terms(loan_case)
    compliance = ComplianceResult(status="PASS", findings=[], confidence=0.10)
    risk = RiskResult(
        score=1,
        band="LOW",
        confidence=0.10,
        primary_risk_factors=[],
        mitigating_factors=["Downstream agents disabled."],
        rationale="Ablation run only extracted terms.",
    )
    return synthesize_review_packet(
        terms=terms,
        compliance=compliance,
        risk=risk,
        validation_errors=[],
    )


def run_single_agent_baseline_stub(loan_case: LoanCase) -> ReviewPacket:
    terms = extract_terms(loan_case)
    compliance = _single_agent_compliance_guess(terms)
    risk = _single_agent_risk_guess(terms)
    return synthesize_review_packet(
        terms=terms,
        compliance=compliance,
        risk=risk,
        validation_errors=[],
    )


def _single_agent_compliance_guess(terms: ExtractedTerms) -> ComplianceResult:
    if terms.prior_default:
        return ComplianceResult(status="FAIL", findings=[], confidence=0.55)
    if terms.missing_documents:
        return ComplianceResult(status="REVIEW", findings=[], confidence=0.50)
    return ComplianceResult(status="PASS", findings=[], confidence=0.60)


def _single_agent_risk_guess(terms: ExtractedTerms) -> RiskResult:
    if terms.prior_default or terms.loan_amount >= 900000:
        band = "HIGH"
        score = 4
    elif terms.borrower_credit_score is None or terms.years_in_business is None:
        band = "MEDIUM"
        score = 3
    else:
        band = "LOW"
        score = 1

    return RiskResult(
        score=score,
        band=band,
        confidence=0.55,
        primary_risk_factors=["Single-agent baseline uses coarse heuristics."],
        mitigating_factors=[],
        rationale="Baseline stub approximates a single prompt without specialist agents.",
    )


def summarize_ablation_table(results: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for config_name, metrics in results.items():
        rows.append({"configuration": config_name, **metrics})
    return rows


if __name__ == "__main__":
    print(json.dumps(summarize_ablation_table(run_ablation_study()), indent=2))
