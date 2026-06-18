"""Prompt templates for optional LangChain agent mode."""

DOCUMENT_PARSE_PROMPT = """You are a loan intake specialist. Parse the following loan application narrative into structured fields.

Return JSON only. Use null for any field that cannot be determined from the text.
Infer the 6-digit NAICS code from the industry description if not stated.
Convert dollar amounts to plain floats (no commas or symbols).
Convert loan term to months (e.g. "5 years" = 60).

{{
  "borrower_name": "string — legal business name",
  "industry": "string — industry description",
  "naics_code": "string — 6-digit NAICS code",
  "loan_amount": float,
  "sba_guaranteed_amount": float or 0,
  "term_months": integer,
  "jobs_supported": integer or 0,
  "borrower_credit_score": integer or null,
  "years_in_business": float or null,
  "prior_default": true or false,
  "missing_documents": ["list", "of", "document", "types", "flagged", "as", "absent"],
  "notes": "one sentence summary of the application"
}}

Loan application narrative:
{document_text}
"""

TERM_EXTRACTION_PROMPT = """You are the Term Extractor Agent for a small business loan review pipeline.

Extract the following fields from the source loan record and return JSON only:
- case_id
- borrower_name
- industry
- naics_code
- loan_amount
- sba_guaranteed_amount
- guarantee_ratio
- term_months
- jobs_supported
- borrower_credit_score
- years_in_business
- prior_default
- missing_documents
- confidence
- warnings

Source loan record:
{loan_case_json}
"""

RISK_RATIONALE_PROMPT = """You are the Credit Risk Scorer Agent for a small business loan review pipeline.

The deterministic risk model has already assigned the risk score and band below.
Write a concise, evidence-grounded rationale for a human loan officer. Do not change the score or band.

Extracted terms:
{terms_json}

Risk result:
{risk_json}

Return JSON only:
{{
  "rationale": ""
}}
"""

COMPLIANCE_RATIONALE_PROMPT = """You are the Compliance Checker Agent for a small business loan review pipeline.

The rules engine has already identified the compliance status and findings below.
Write a concise, evidence-grounded reviewer note. Do not change the status or findings.

Extracted terms:
{terms_json}

Compliance result:
{compliance_json}

Return JSON only:
{{
  "reviewer_note": ""
}}
"""

