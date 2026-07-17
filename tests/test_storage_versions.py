import pytest
from app.storage.versions import VersionStore, ProposalRecord
from app.models.domain import DocumentGraph, ProposalState
from app.core.errors import VersionConflictError, NotFoundError

def test_version_store_save_and_get():
    store = VersionStore()
    graph = DocumentGraph(
        document_id="doc_test1",
        version=1,
        package_sha256="abc123sha"
    )
    store.save_version("sess_1", 1, b"raw_v1", graph)
    
    rec = store.get_version("sess_1", 1)
    assert rec.version == 1
    assert rec.raw_bytes == b"raw_v1"
    assert rec.package_sha256 == "abc123sha"

    with pytest.raises(VersionConflictError):
        store.save_version("sess_1", 1, b"raw_v1_dup", graph)

    with pytest.raises(NotFoundError):
        store.get_version("sess_1", 99)

def test_proposal_commit_flow():
    store = VersionStore()
    graph_v1 = DocumentGraph(document_id="doc_test1", version=1, package_sha256="hash1")
    store.save_version("sess_2", 1, b"v1_bytes", graph_v1)

    graph_v2 = DocumentGraph(document_id="doc_test1", version=2, package_sha256="hash2")
    prop = ProposalRecord(
        proposal_id="prop_1",
        session_id="sess_2",
        base_version=1,
        plan=None,
        instruction_summary="Edit test",
        operations=[],
        diff=[],
        citation_report={},
        proposal_docx_bytes=b"v2_bytes",
        proposal_graph=graph_v2
    )
    store.save_proposal(prop)
    assert prop.state == ProposalState.PROPOSAL_READY

    new_v = store.commit_proposal("prop_1", current_session_version=1)
    assert new_v.version == 2
    assert new_v.raw_bytes == b"v2_bytes"
    assert new_v.parent_version == 1
    assert prop.state == ProposalState.COMMITTED

    # Check version conflict if someone tries to commit when session is already at v2
    prop_stale = ProposalRecord(
        proposal_id="prop_stale",
        session_id="sess_2",
        base_version=1,
        plan=None,
        instruction_summary="Stale edit",
        operations=[],
        diff=[],
        citation_report={},
        proposal_docx_bytes=b"stale_bytes",
        proposal_graph=graph_v2
    )
    store.save_proposal(prop_stale)
    with pytest.raises(VersionConflictError) as exc:
        store.commit_proposal("prop_stale", current_session_version=2)
    assert "Proposal base_version (1) does not match current session version (2)" in str(exc.value)
