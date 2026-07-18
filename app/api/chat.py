from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.models.domain import (
    EditPlan,
    ProposalState,
    SessionState,
)
from app.storage.sessions import session_store
from app.storage.versions import version_store
from app.docx.package import OpcPackage
from app.docx.inspector import DocxInspector
from app.docx.executor import DocxMutationExecutor
from app.docx.serializer import DocxSerializer
from app.verification.pipeline import VerificationPipeline
from app.agents.planner import EditPlannerAgent
from app.agents.verifier import SemanticVerifierAgent, SemanticVerificationReport
from app.api.proposals import ProposalResponse
from app.core.errors import PreconditionFailedError, PlanValidationError, NotFoundError

router = APIRouter(prefix="/sessions", tags=["chat"])

class AgentPlanRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=10000, description="Natural language prompt specifying desired academic edits.")
    explicit_node_ids: Optional[List[str]] = Field(default=None, description="Optional explicit node IDs to restrict scope.")
    explicit_chapter_ids: Optional[List[str]] = Field(default=None, description="Optional explicit chapter IDs to restrict scope.")
    reference_store: Optional[Dict[str, Any]] = Field(default=None, description="Available reference assets.")
    run_semantic_verifier: bool = Field(default=True, description="Whether to run advisory semantic check on generated diffs.")

class AgentPlanResponse(BaseModel):
    plan: EditPlan
    proposal: ProposalResponse
    semantic_verifier_report: Optional[SemanticVerificationReport] = None

@router.post("/{session_id}/chat", response_model=AgentPlanResponse, status_code=status.HTTP_201_CREATED)
def plan_and_create_proposal(session_id: str, req: AgentPlanRequest):
    session = session_store.get_session(session_id)
    if not session:
        raise NotFoundError("Session")

    if session.state not in (SessionState.READY, SessionState.PROPOSAL_READY, SessionState.AWAITING_APPROVAL):
        raise PreconditionFailedError(f"Session is in invalid state for planning: {session.state}")

    current_version_record = version_store.get_version(session_id, session.current_version)
    if not current_version_record:
        raise NotFoundError("Current version")

    original_pkg = OpcPackage(current_version_record.docx_bytes)
    base_inspector = DocxInspector(original_pkg)
    base_graph = base_inspector.build_graph()
    root = original_pkg.get_xml_tree(original_pkg.main_document_part)

    # 1. Invoke EditPlannerAgent to generate and validate EditPlan
    planner = EditPlannerAgent()
    available_ref_ids = list(req.reference_store.keys()) if req.reference_store else []
    try:
        plan = planner.plan(
            graph=base_graph,
            instruction=req.instruction,
            explicit_node_ids=req.explicit_node_ids,
            explicit_chapter_ids=req.explicit_chapter_ids,
            available_reference_ids=available_ref_ids
        )
    except PlanValidationError as e:
        raise HTTPException(status_code=422, detail=f"Agent planning failed schema or semantic checks: {str(e)}")

    # Ensure document_id and document_version match active session graph
    plan.document_id = base_graph.document_id
    plan.document_version = base_graph.version

    # Auto-resolve placeholder expected_text_hash from active document graph
    node_map = {n.node_id: n for n in base_graph.nodes}
    for op in plan.operations:
        if getattr(op, "target", None) and op.target.node_id in node_map:
            n = node_map[op.target.node_id]
            if op.target.expected_text_hash in ("sha256:will_be_resolved", "sha256:will_be_calculated", "sha256:resolved", "", None) or not op.target.expected_text_hash.startswith("sha256:"):
                op.target.expected_text_hash = n.text_hash

    # 2. Execute mutations deterministically
    executor = DocxMutationExecutor(root, base_graph, reference_store=req.reference_store)
    try:
        diffs = executor.execute_operations(plan.operations)
    except PreconditionFailedError as e:
        raise HTTPException(status_code=412, detail=str(e))

    # 3. Serialize proposed package
    serializer = DocxSerializer(original_pkg)
    proposal_bytes, _ = serializer.serialize({original_pkg.main_document_part: root})

    # 4. Inspect proposed package
    proposal_pkg = OpcPackage(proposal_bytes)
    proposal_graph = DocxInspector(proposal_pkg).build_graph()

    # 5. Run Verification Pipeline
    pipeline = VerificationPipeline()
    report = pipeline.run_pipeline(proposal_bytes, base_graph, proposal_graph, plan=plan)

    if report.blocking_pass:
        prop_state = ProposalState.AWAITING_APPROVAL
        session.state = SessionState.AWAITING_APPROVAL
    else:
        prop_state = ProposalState.VERIFICATION_FAILED
        session.state = SessionState.VERIFICATION_FAILED
    session_store.save_session(session)

    # 6. Save Proposal Record
    proposal_id = f"prop_{len(version_store.list_proposals(session_id)) + 1}"
    version_store.create_proposal(
        proposal_id=proposal_id,
        session_id=session_id,
        base_version=session.current_version,
        plan=plan,
        diffs=diffs,
        verification_report=report,
        proposal_bytes=proposal_bytes,
        proposal_graph=proposal_graph,
        status=prop_state
    )

    prop_resp = ProposalResponse(
        proposal_id=proposal_id,
        session_id=session_id,
        base_version=session.current_version,
        status=prop_state,
        diff=diffs,
        verification_report=report
    )

    # 7. Optional Semantic Verification
    verifier_report = None
    if req.run_semantic_verifier:
        verifier = SemanticVerifierAgent()
        verifier_report = verifier.verify_proposal(req.instruction, diffs, plan=plan)

    return AgentPlanResponse(
        plan=plan,
        proposal=prop_resp,
        semantic_verifier_report=verifier_report
    )
