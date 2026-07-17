from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.domain import DocumentGraph, EditPlan, ProposalState, ProposalSummary
from app.core.errors import NotFoundError, VersionConflictError

class DocumentVersionRecord:
    def __init__(
        self,
        session_id: str,
        version: int,
        raw_bytes: bytes,
        graph: DocumentGraph,
        parent_version: Optional[int] = None,
        proposal_id: Optional[str] = None,
        commit_message: str = "",
        user_id: str = "system"
    ):
        self.session_id = session_id
        self.version = version
        self.version_num = version
        self.document_id = graph.document_id
        self.docx_bytes = raw_bytes
        self.raw_bytes = raw_bytes
        self.graph = graph
        self.package_sha256 = graph.package_sha256
        self.parent_version = parent_version
        self.proposal_id = proposal_id
        self.commit_message = commit_message or f"Version {version}"
        self.user_id = user_id
        self.created_at = datetime.now(timezone.utc)

class ProposalRecord:
    def __init__(
        self,
        proposal_id: str,
        session_id: str,
        base_version: int,
        plan: Optional[EditPlan] = None,
        instruction_summary: str = "",
        operations: Optional[List[Any]] = None,
        diff: Optional[List[Any]] = None,
        diffs: Optional[List[Any]] = None,
        citation_report: Optional[Dict[str, Any]] = None,
        verification_report: Optional[Any] = None,
        proposal_docx_bytes: Optional[bytes] = None,
        proposal_graph: Optional[DocumentGraph] = None,
        status: ProposalState = ProposalState.PROPOSAL_READY
    ):
        self.proposal_id = proposal_id
        self.session_id = session_id
        self.base_version = base_version
        self.plan = plan
        self.instruction_summary = instruction_summary or (plan.instruction_summary if plan else "")
        self.operations = operations or (plan.operations if plan else [])
        self.diffs = diffs or diff or []
        self.diff = self.diffs  # backward compat
        self.citation_report = citation_report or {}
        self.verification_report = verification_report
        self.verification = verification_report
        self.warnings: List[str] = []
        self.status = status
        self.state = status
        self.proposal_docx_bytes = proposal_docx_bytes
        self.proposal_graph = proposal_graph
        self.created_at = datetime.now(timezone.utc)

    def to_summary(self) -> ProposalSummary:
        return ProposalSummary(
            proposal_id=self.proposal_id,
            state=self.state,
            base_version=self.base_version,
            instruction_summary=self.instruction_summary,
            operations=self.operations,
            diff=self.diffs,
            citation_report=self.citation_report,
            verification=self.verification_report,
            warnings=self.warnings
        )

class VersionStore:
    """Store for immutable document versions and active proposals."""
    def __init__(self):
        # (session_id, version) -> DocumentVersionRecord
        self._versions: Dict[tuple[str, int], DocumentVersionRecord] = {}
        # proposal_id -> ProposalRecord
        self._proposals: Dict[str, ProposalRecord] = {}

    def save_version(
        self,
        session_id: str,
        version: int,
        raw_bytes: bytes,
        graph: DocumentGraph,
        parent_version: Optional[int] = None,
        proposal_id: Optional[str] = None,
        commit_message: str = "",
        user_id: str = "system"
    ) -> DocumentVersionRecord:
        key = (session_id, version)
        if key in self._versions:
            raise VersionConflictError(f"Version {version} already exists for session {session_id}.")
        record = DocumentVersionRecord(
            session_id=session_id,
            version=version,
            raw_bytes=raw_bytes,
            graph=graph,
            parent_version=parent_version,
            proposal_id=proposal_id,
            commit_message=commit_message,
            user_id=user_id
        )
        self._versions[key] = record
        return record

    def get_version(self, session_id: str, version: int) -> DocumentVersionRecord:
        key = (session_id, version)
        if key not in self._versions:
            raise NotFoundError(f"Version {version} for session '{session_id}'")
        return self._versions[key]

    def list_versions(self, session_id: str) -> List[DocumentVersionRecord]:
        return sorted([r for (sid, _), r in self._versions.items() if sid == session_id], key=lambda x: x.version)

    def create_proposal(self, proposal_id: str, session_id: str, base_version: int, plan: Any, diffs: Any, verification_report: Any, proposal_bytes: bytes, proposal_graph: DocumentGraph, status: ProposalState) -> ProposalRecord:
        record = ProposalRecord(
            proposal_id=proposal_id,
            session_id=session_id,
            base_version=base_version,
            plan=plan,
            diffs=diffs,
            verification_report=verification_report,
            proposal_docx_bytes=proposal_bytes,
            proposal_graph=proposal_graph,
            status=status
        )
        return self.save_proposal(record)

    def save_proposal(self, record: ProposalRecord) -> ProposalRecord:
        self._proposals[record.proposal_id] = record
        return record

    def get_proposal(self, session_id: str, proposal_id: str) -> ProposalRecord:
        if proposal_id not in self._proposals:
            raise NotFoundError(f"Proposal '{proposal_id}'")
        prop = self._proposals[proposal_id]
        if prop.session_id != session_id:
            raise NotFoundError(f"Proposal '{proposal_id}' for session '{session_id}'")
        return prop

    def list_proposals(self, session_id: str) -> List[ProposalRecord]:
        return [p for p in self._proposals.values() if p.session_id == session_id]

    def commit_proposal(self, session_id: str, proposal_id: Any = None, commit_message: str = "", user_id: str = "system", current_session_version: Optional[int] = None) -> DocumentVersionRecord:
        if isinstance(proposal_id, int) or (proposal_id is None and current_session_version is not None):
            # Called as commit_proposal(proposal_id="prop_1", current_session_version=1) or commit_proposal("prop_1", 1)
            real_proposal_id = session_id
            if real_proposal_id not in self._proposals:
                raise NotFoundError(f"Proposal '{real_proposal_id}'")
            prop = self._proposals[real_proposal_id]
            curr_ver = proposal_id if isinstance(proposal_id, int) else current_session_version
            if prop.base_version != curr_ver:
                raise VersionConflictError(f"Proposal base_version ({prop.base_version}) does not match current session version ({curr_ver}).")
        else:
            # Called as commit_proposal(session_id="sess_1", proposal_id="prop_1", ...)
            prop = self.get_proposal(session_id, str(proposal_id))

        if prop.status != ProposalState.PROPOSAL_READY and prop.status != ProposalState.AWAITING_APPROVAL:
            raise VersionConflictError(f"Cannot commit proposal in state: {prop.status}")
        if not prop.proposal_docx_bytes or not prop.proposal_graph:
            raise VersionConflictError("Proposal lacks generated DOCX or verification graph.")

        new_version = prop.base_version + 1
        record = self.save_version(
            session_id=prop.session_id,
            version=new_version,
            raw_bytes=prop.proposal_docx_bytes,
            graph=prop.proposal_graph,
            parent_version=prop.base_version,
            proposal_id=prop.proposal_id,
            commit_message=commit_message,
            user_id=user_id
        )
        prop.status = ProposalState.COMMITTED
        prop.state = ProposalState.COMMITTED
        return record

    def clear_for_testing(self) -> None:
        self._versions.clear()
        self._proposals.clear()

version_store = VersionStore()
