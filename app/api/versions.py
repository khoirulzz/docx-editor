from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from app.models.domain import ProposalState, SessionState
from app.storage.sessions import session_store
from app.storage.versions import version_store, DocumentVersionRecord
from app.core.errors import PreconditionFailedError

router = APIRouter(prefix="/sessions", tags=["versions"])

class CommitRequest(BaseModel):
    commit_message: str = "Applied changes"
    user_id: Optional[str] = "system"

class VersionSummary(BaseModel):
    document_id: str
    version_num: int
    parent_version: Optional[int]
    created_at: str
    commit_message: str

@router.post("/{session_id}/proposals/{proposal_id}/commit", response_model=VersionSummary)
def commit_proposal(session_id: str, proposal_id: str, req: Optional[CommitRequest] = None):
    req = req or CommitRequest()
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    proposal = version_store.get_proposal(session_id, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    if proposal.status == ProposalState.VERIFICATION_FAILED or not proposal.verification_report.blocking_pass:
        raise HTTPException(
            status_code=412,
            detail="Precondition failed: Cannot commit a proposal that failed blocking verification checks."
        )

    if proposal.status == ProposalState.COMMITTED:
        raise HTTPException(status_code=400, detail="Proposal is already committed.")

    try:
        new_record = version_store.commit_proposal(
            session_id=session_id,
            proposal_id=proposal_id,
            commit_message=req.commit_message,
            user_id=req.user_id or "system"
        )
    except PreconditionFailedError as e:
        raise HTTPException(status_code=412, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Update session state to COMMITTED / READY with new version
    session.current_version = new_record.version_num
    session.state = SessionState.COMMITTED
    session_store.save_session(session)

    return VersionSummary(
        document_id=new_record.document_id,
        version_num=new_record.version_num,
        parent_version=new_record.parent_version,
        created_at=new_record.created_at.isoformat(),
        commit_message=new_record.commit_message
    )

@router.get("/{session_id}/versions", response_model=List[VersionSummary])
def list_versions(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    records = version_store.list_versions(session_id)
    return [
        VersionSummary(
            document_id=r.document_id,
            version_num=r.version_num,
            parent_version=r.parent_version,
            created_at=r.created_at.isoformat(),
            commit_message=r.commit_message
        )
        for r in records
    ]

@router.get("/{session_id}/versions/{version_num}/export")
def export_version(session_id: str, version_num: int):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    record = version_store.get_version(session_id, version_num)
    if not record:
        raise HTTPException(status_code=404, detail="Version not found.")

    return Response(
        content=record.docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{record.document_id}_v{version_num}.docx"'}
    )
