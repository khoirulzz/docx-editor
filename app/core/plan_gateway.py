import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from app.core.errors import PlanValidationError
from app.models.domain import EditPlan

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
            try:
                data = json.loads(raw_plan_json)
            except json.JSONDecodeError as e:
                raise PlanValidationError("LLM output is not valid JSON.", details={"error": str(e)})
        else:
            data = raw_plan_json

        # Validate with Pydantic model (which strictly mirrors schema)
        try:
            plan = EditPlan.model_validate(data)
        except Exception as e:
            raise PlanValidationError("Edit plan failed schema validation.", details={"error": str(e)})

        # Semantic check: no hallucinated references
        if available_reference_ids is not None:
            avail_set = set(available_reference_ids)
            for ref_id in plan.used_reference_ids:
                if ref_id not in avail_set:
                    raise PlanValidationError(
                        f"Hallucinated reference ID: {ref_id}. Must only use provided reference IDs.",
                        details={"hallucinated_id": ref_id}
                    )

        return plan
