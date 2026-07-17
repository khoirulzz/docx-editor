import json
import logging
from typing import Any, Dict, List, Optional
from app.models.domain import DocumentGraph, EditPlan
from app.agents.client import LLMClient
from app.agents.scope import ScopeSelector, ContextPruner
from app.core.plan_gateway import PlanGateway
from app.core.errors import PlanValidationError

logger = logging.getLogger(__name__)

SYSTEM_RULES_PREFIX = """You are the AI DOCX Academic Editor (EditPlannerAgent).
Your SOLE responsibility is to output a single JSON object conforming strictly to the EditPlan schema.
NEVER output raw XML, XPath, file paths, or arbitrary markdown commentary outside the JSON object.
Every text change or paragraph insertion must be represented by deterministic, typed operations inside the JSON.
All citations must reference exact normalized IDs provided in the references section (no hallucinated sources or IDs)."""

EDIT_PLAN_SCHEMA_PROMPT = """JSON Output Specification (EditPlan):
Your response MUST be a JSON object containing:
- schema_version: "edit-plan/1.0"
- document_id: string matching "^doc_[A-Za-z0-9_-]+$"
- document_version: integer (must match active document_version)
- instruction_summary: string explaining what changed
- scope: { "allowed_node_ids": [array of node IDs modified] }
- operations: array of operation objects. Supported operation types:
  * replace_text_span: { "type": "replace_text_span", "operation_id": "op_1", "target": { "node_id": "para_X", "expected_text_hash": "sha256:will_be_resolved" }, "expected_text": "Exact substring to replace", "replacement_content": [ { "type": "text", "text": "New text string" } ] }
  * insert_paragraph_after: { "type": "insert_paragraph_after", "operation_id": "op_2", "target": { "node_id": "para_X" }, "paragraph_style_policy": { "style_id": "Normal" }, "content": [ { "type": "text", "text": "New paragraph text" } ] }
  * insert_paragraph_before: { "type": "insert_paragraph_before", "operation_id": "op_3", "target": { "node_id": "para_X" }, "paragraph_style_policy": { "style_id": "Normal" }, "content": [ { "type": "text", "text": "New paragraph text" } ] }
- used_reference_ids: array of reference ID strings (e.g. ["REF-001"]) used in citations
- used_evidence_ids: array of evidence ID strings
- unsupported_claims: array of { "claim": string, "reason": string }
- warnings: array of strings
- assumptions: array of strings"""

POLICY_SUMMARY = """Document Policy & Guidelines:
1. Maintain academic tone and standard Indonesian/English academic conventions.
2. Do not modify protected boundaries or existing legacy Mendeley/Cite fields unless explicitly instructed.
3. Keep operations focused and minimal."""

class EditPlannerAgent:
    """
    Orchestrates prompt construction, LLM generation, and bounded repair retries
    via strict PlanGateway validation.
    """
    def __init__(self, client: Optional[LLMClient] = None, gateway: Optional[PlanGateway] = None):
        self.client = client or LLMClient()
        self.gateway = gateway or PlanGateway()

    def build_system_prompt(self) -> str:
        """Assembles prompt prefixes in order for stable caching."""
        return f"{SYSTEM_RULES_PREFIX}\n\n{EDIT_PLAN_SCHEMA_PROMPT}\n\n{POLICY_SUMMARY}"

    def build_user_prompt(
        self,
        instruction: str,
        document_slice: str,
        references_slice: str = ""
    ) -> str:
        prompt_parts = [
            f"=== USER INSTRUCTION ===\n{instruction}",
            f"\n=== DOCUMENT CONTEXT ===\n{document_slice}"
        ]
        if references_slice:
            prompt_parts.append(f"\n=== AVAILABLE REFERENCES & EVIDENCE ===\n{references_slice}")
        prompt_parts.append("\nOutput ONLY the JSON object conforming to EditPlan:")
        return "\n".join(prompt_parts)

    def plan(
        self,
        graph: DocumentGraph,
        instruction: str,
        explicit_node_ids: Optional[List[str]] = None,
        explicit_chapter_ids: Optional[List[str]] = None,
        available_reference_ids: Optional[List[str]] = None,
        references_slice: str = ""
    ) -> EditPlan:
        # 1. Select scope
        selected_node_ids, selected_chapter_ids = ScopeSelector.select_scope(
            graph=graph,
            instruction_text=instruction,
            explicit_node_ids=explicit_node_ids,
            explicit_chapter_ids=explicit_chapter_ids
        )

        # 2. Format pruned document slice
        doc_slice = ContextPruner.format_document_slice(
            graph=graph,
            allowed_node_ids=selected_node_ids,
            allowed_chapter_ids=selected_chapter_ids
        )

        # 3. Build prompts
        system_prompt = self.build_system_prompt()
        user_prompt = self.build_user_prompt(
            instruction=instruction,
            document_slice=doc_slice,
            references_slice=references_slice
        )

        # 4. Generate initial plan JSON
        raw_json_str = self.client.generate_plan_json(system_prompt, user_prompt)

        # 5. Validate with PlanGateway + 1 Bounded Repair Retry
        try:
            return self.gateway.validate_plan(raw_json_str, available_reference_ids=available_reference_ids)
        except PlanValidationError as err:
            logger.warning(f"Initial EditPlan failed validation: {err}. Attempting 1 repair retry...")
            repair_json_str = self.client.repair_plan_json(
                system_prompt=system_prompt,
                previous_output=raw_json_str,
                validation_errors=str(err)
            )
            # If second attempt fails, let PlanValidationError bubble up (fail closed)
            return self.gateway.validate_plan(repair_json_str, available_reference_ids=available_reference_ids)
