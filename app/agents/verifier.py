import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.domain import EditPlan
from app.agents.client import LLMClient

logger = logging.getLogger(__name__)

class SemanticVerificationReport(BaseModel):
    advisory_pass: bool = Field(default=True, description="Whether the changes semantically satisfy academic & instruction criteria.")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    coherence_check: bool = Field(default=True)
    academic_tone_check: bool = Field(default=True)
    instruction_compliance_check: bool = Field(default=True)
    feedback_notes: List[str] = Field(default_factory=list)

VERIFIER_SYSTEM_PROMPT = """You are the AI DOCX Academic Editor Semantic Verifier (SemanticVerifierAgent).
Your job is to review proposed text diffs (before vs after) and evaluate if they:
1. Comply with the user's instruction.
2. Maintain natural academic tone and coherence.
3. Avoid unwanted repetition, redundancy, or grammatical regressions.

Output ONLY a JSON object:
{
  "advisory_pass": boolean,
  "confidence_score": float (0.0 to 1.0),
  "coherence_check": boolean,
  "academic_tone_check": boolean,
  "instruction_compliance_check": boolean,
  "feedback_notes": [array of short feedback strings]
}"""

class SemanticVerifierAgent:
    """
    Advisory review agent for proposed document edits. Does not override deterministic
    verification (L1-L5), but provides semantic guidance for user decisions.
    """
    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    def verify_proposal(self, instruction: str, diffs: List[Any], plan: Optional[EditPlan] = None) -> SemanticVerificationReport:
        if not diffs:
            return SemanticVerificationReport(
                advisory_pass=True,
                confidence_score=1.0,
                feedback_notes=["No diff items generated for review."]
            )

        # Prepare diff summary (limited before/after pairs to save tokens)
        diff_summaries = []
        for d in diffs[:20]: # Limit to first 20 diff items
            if hasattr(d, "model_dump"):
                d_dict = d.model_dump()
            elif isinstance(d, dict):
                d_dict = d
            else:
                continue
            diff_summaries.append({
                "node_id": d_dict.get("node_id", ""),
                "before": d_dict.get("before_text", ""),
                "after": d_dict.get("after_text", "")
            })

        user_prompt = (
            f"=== USER INSTRUCTION ===\n{instruction}\n\n"
            f"=== PROPOSED DIFFS (Before vs After) ===\n{json.dumps(diff_summaries, indent=2, ensure_ascii=False)}\n\n"
            f"Output the JSON evaluation report:"
        )

        try:
            raw_json_str = self.client.generate_plan_json(VERIFIER_SYSTEM_PROMPT, user_prompt)
            data = json.loads(raw_json_str)
            return SemanticVerificationReport.model_validate(data)
        except Exception as e:
            logger.warning(f"Semantic verification check encountered error or invalid JSON: {e}. Defaulting to pass.")
            return SemanticVerificationReport(
                advisory_pass=True,
                confidence_score=0.8,
                feedback_notes=[f"Semantic check skipped due to error: {str(e)}"]
            )
