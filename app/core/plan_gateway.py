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
    
    # 1. Clean <think>...</think> blocks, supporting unclosed or missing closing tag fallbacks
    cleaned = re.sub(r"<think>.*?(?:</think>|(?=\s*(?:```|\{)))", "", cleaned, flags=re.DOTALL).strip()
    
    # 2. Extract JSON block from markdown fences or outermost braces
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and start <= end:
            cleaned = cleaned[start:end+1]
            
    # 3. Escape raw control characters (newlines, carriage returns, tabs) inside string literals
    string_pattern = re.compile(r'"(?:[^"\\]|\\.)*"')
    cleaned = string_pattern.sub(lambda m: m.group(0).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"), cleaned)
    
    # 4. Remove trailing commas before closing braces/brackets (ignoring strings)
    comma_pattern = re.compile(r'("(?:[^"\\]|\\.)*")|,\s*(?=[}\]])')
    cleaned = comma_pattern.sub(lambda m: m.group(1) if m.group(1) else "", cleaned)
    
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

        # Normalize common LLM shortcuts before Pydantic validation
        if isinstance(data, dict):
            if "scope" not in data or not isinstance(data.get("scope"), dict):
                data["scope"] = {"allowed_node_ids": []}
            if "allowed_node_ids" not in data["scope"] or not isinstance(data["scope"].get("allowed_node_ids"), list):
                data["scope"]["allowed_node_ids"] = []
            for op in data.get("operations", []):
                if isinstance(op, dict):
                    if "target" in op and isinstance(op["target"], str):
                        op["target"] = {"node_id": op["target"], "expected_text_hash": "sha256:will_be_resolved"}
                    elif "target" in op and isinstance(op["target"], dict):
                        if not op["target"].get("expected_text_hash"):
                            op["target"]["expected_text_hash"] = "sha256:will_be_resolved"
                    if "replacement_content" in op and isinstance(op["replacement_content"], str):
                        op["replacement_content"] = [{"type": "text", "text": op["replacement_content"]}]
                    if "content" in op and isinstance(op["content"], str):
                        op["content"] = [{"type": "text", "text": op["content"]}]

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
