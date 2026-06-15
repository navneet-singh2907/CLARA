"""LLM-as-judge rubric for loan review outputs."""

JUDGE_RUBRIC = """You are evaluating a loan review agent output.

Score each dimension from 1 to 5:
1. Faithfulness: Are all claims grounded in the source document and extracted fields?
2. Completeness: Were all key loan terms and compliance-relevant facts captured?
3. Risk calibration: Is the risk rating justified by evidence?
4. Compliance accuracy: Were the correct compliance concerns identified?
5. Explainability: Could a loan officer act on this output?

Return JSON only.
"""

