from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.models.domain import (
    DiffItem,
    EditPlan,
    ProposalState,
    SessionState,
    VerificationReport,
)
from app.storage.sessions import session_store
from app.storage.versions import version_store
from app.docx.package import OpcPackage
from app.docx.inspector import DocxInspector
from app.docx.executor import DocxMutationExecutor
from app.docx.serializer import DocxSerializer
from app.verification.pipeline import VerificationPipeline
from app.core.errors import PreconditionFailedError, NotFoundError

router = APIRouter(prefix="/sessions", tags=["proposals"])

class ProposalCreationRequest(BaseModel):
    plan: EditPlan
    reference_store: Optional[Dict[str, Any]] = None

class ProposalResponse(BaseModel):
    proposal_id: str
    session_id: str
    base_version: int
    status: ProposalState
    diff: List[DiffItem]
    verification_report: VerificationReport

class DiffDecisionRequest(BaseModel):
    operation_id: str
    decision: str  # "accepted" or "rejected"

@router.post("/{session_id}/proposals", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
def create_proposal(session_id: str, req: ProposalCreationRequest):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.state not in (SessionState.READY, SessionState.PROPOSAL_READY, SessionState.AWAITING_APPROVAL):
        raise HTTPException(status_code=400, detail=f"Session is in invalid state for planning: {session.state}")

    current_version_record = version_store.get_version(session_id, session.current_version)
    if not current_version_record:
        raise HTTPException(status_code=404, detail="Current version not found.")

    # 1. Parse current package & inspect graph
    original_pkg = OpcPackage(current_version_record.docx_bytes)
    base_inspector = DocxInspector(original_pkg)
    base_graph = base_inspector.build_graph()
    root = original_pkg.get_xml_tree(original_pkg.main_document_part)

    # 2. Execute mutations
    executor = DocxMutationExecutor(root, base_graph, reference_store=req.reference_store)
    try:
        diffs = executor.execute_operations(req.plan.operations)
    except PreconditionFailedError as e:
        raise HTTPException(status_code=412, detail=str(e))

    # 3. Serialize proposed package
    serializer = DocxSerializer(original_pkg)
    proposal_bytes, proposal_sha256 = serializer.serialize({original_pkg.main_document_part: root})

    # 4. Inspect proposed package
    proposal_pkg = OpcPackage(proposal_bytes)
    proposal_graph = DocxInspector(proposal_pkg).build_graph()

    # 5. Run Verification Pipeline
    pipeline = VerificationPipeline()
    report = pipeline.run_pipeline(proposal_bytes, base_graph, proposal_graph, plan=req.plan)

    # 6. Determine Proposal & Session state
    if report.blocking_pass:
        prop_state = ProposalState.AWAITING_APPROVAL
        session.state = SessionState.AWAITING_APPROVAL
    else:
        prop_state = ProposalState.VERIFICATION_FAILED
        session.state = SessionState.VERIFICATION_FAILED
    session_store.save_session(session)

    # 7. Save Proposal Record in VersionStore
    proposal_id = f"prop_{len(version_store.list_proposals(session_id)) + 1}"
    version_store.create_proposal(
        proposal_id=proposal_id,
        session_id=session_id,
        base_version=session.current_version,
        plan=req.plan,
        diffs=diffs,
        verification_report=report,
        proposal_bytes=proposal_bytes,
        proposal_graph=proposal_graph,
        status=prop_state
    )

    return ProposalResponse(
        proposal_id=proposal_id,
        session_id=session_id,
        base_version=session.current_version,
        status=prop_state,
        diff=diffs,
        verification_report=report
    )

@router.get("/{session_id}/proposals/{proposal_id}", response_model=ProposalResponse)
def get_proposal(session_id: str, proposal_id: str):
    record = version_store.get_proposal(session_id, proposal_id)
    if not record:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    return ProposalResponse(
        proposal_id=record.proposal_id,
        session_id=record.session_id,
        base_version=record.base_version,
        status=record.status,
        diff=record.diffs,
        verification_report=record.verification_report
    )

@router.post("/{session_id}/proposals/{proposal_id}/decisions", response_model=ProposalResponse)
def make_decisions(session_id: str, proposal_id: str, decisions: List[DiffDecisionRequest]):
    record = version_store.get_proposal(session_id, proposal_id)
    if not record:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    dec_map = {d.operation_id: d.decision for d in decisions}
    for diff in record.diffs:
        if diff.operation_id in dec_map:
            diff.status = dec_map[diff.operation_id]

    version_store.save_proposal(record)
    return ProposalResponse(
        proposal_id=record.proposal_id,
        session_id=record.session_id,
        base_version=record.base_version,
        status=record.status,
        diff=record.diffs,
        verification_report=record.verification_report
    )
