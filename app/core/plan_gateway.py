import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from app.core.errors import PlanValidationError
from app.models.domain import EditPlan

import re

def _clean_and_extract_json(text: str) -> str:
    if not isinstance(text, str):
        return text
    cleaned = text.strip()
    # Strip <think>...</think> blocks common in reasoning models
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
    # Check for markdown code fences (```json ... ``` or ``` ... ```)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    # If no fences or invalid JSON, try finding outermost braces
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and start <= end:
        return cleaned[start:end+1]
    return cleaned

class PlanGateway:
    """Strict JSON Schema & Semantic validation gateway for LLM EditPlans."""
    def __init__(self, schema_path: Optional[Path] = None):
        if schema_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            schema_path = root / "schemas" / "edit-plan.schema.json"
        self.schema_path = schema_path
        self._schema_dict: Optional[Dict[str, Any]] = None

    def validate_plan(self, raw_plan_json: Union[str, Dict[str, Any]], available_reference_ids: List[str] = None) -> EditPlan:
        """Validates that output conforms to edit-plan schema and passes semantic checks."""
        if isinstance(raw_plan_json, str):
            cleaned_json = _clean_and_extract_json(raw_plan_json)
            try:
                data = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                raise PlanValidationError("LLM output is not valid JSON.", details={"error": str(e), "raw_output": raw_plan_json[:500]})
        else:
            data = raw_plan_json

        # Validate with Pydantic model (which strictly mirrors schema)
        try:
            plan = EditPlan.model_validate(data)
        except Exception as e:
            raise PlanValidationError("Edit plan failed schema validation.", details={"error": str(e)})

        # Semantic check: no hallucinated references
        if available_reference_ids is not None:
            if len(available_reference_ids) == 0:
                # If no reference store is active/uploaded, any ID in used_reference_ids (e.g. dummy REF-001 from prompt example)
                # is sanitized out so general docx editing/rewriting proceeds smoothly without false positive hallucination errors.
                plan.used_reference_ids = []
            else:
                avail_set = set(available_reference_ids)
                for ref_id in plan.used_reference_ids:
                    if ref_id not in avail_set:
                        raise PlanValidationError(
                            f"Hallucinated reference ID: {ref_id}. Must only use provided reference IDs.",
                            details={"hallucinated_id": ref_id}
                        )

        return plan
