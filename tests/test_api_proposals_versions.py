import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.domain import (
    EditPlan,
    EditPlanScope,
    ReplaceTextSpanOperation,
    TargetLocator,
    TextContentBlock,
)
from app.storage.sessions import session_store
from app.storage.versions import version_store
from tests.test_package_security import create_mock_docx

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_stores():
    session_store.clear_for_testing()
    version_store.clear_for_testing()
    yield
    session_store.clear_for_testing()
    version_store.clear_for_testing()

def test_full_proposal_and_commit_flow():
    # 1. Upload initial session
    mock_xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Old text inside paragraph.</w:t></w:r></w:p></w:body></w:document>'
    docx_bytes = create_mock_docx({"word/document.xml": mock_xml})
    
    upload_res = client.post(
        "/v1/sessions",
        files={"file": ("test.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert upload_res.status_code == 201
    session_id = upload_res.json()["session_id"]

    # 2. Inspect session
    inspect_res = client.get(f"/v1/sessions/{session_id}")
    assert inspect_res.status_code == 200
    assert inspect_res.json()["state"] == "READY"

    # 3. Create proposal
    plan = EditPlan(
        document_id="doc_1",
        document_version=1,
        instruction_summary="Replace Old text with New text",
        scope=EditPlanScope(allowed_node_ids=["para_0"]),
        operations=[
            ReplaceTextSpanOperation(
                operation_id="op_1",
                target=TargetLocator(node_id="para_0", expected_text_hash="sha256:will_be_resolved_or_checked"),
                expected_text="Old text",
                replacement_content=[TextContentBlock(text="New text")]
            )
        ]
    )
    # We need exact hash for target node from inspect graph or let's fetch graph first
    # Or compute exact hash of "Old text inside paragraph."
    import hashlib
    target_hash = f"sha256:{hashlib.sha256(b'Old text inside paragraph.').hexdigest()}"
    plan.operations[0].target.expected_text_hash = target_hash

    prop_res = client.post(
        f"/v1/sessions/{session_id}/proposals",
        json={"plan": plan.model_dump()}
    )
    assert prop_res.status_code == 201
    proposal_data = prop_res.json()
    proposal_id = proposal_data["proposal_id"]
    assert proposal_data["status"] == "AWAITING_APPROVAL"
    assert proposal_data["verification_report"]["blocking_pass"] is True
    assert proposal_data["diff"][0]["after_text"] == "New text inside paragraph."

    # 4. Make decisions (accept diff)
    dec_res = client.post(
        f"/v1/sessions/{session_id}/proposals/{proposal_id}/decisions",
        json=[{"operation_id": "op_1", "decision": "accepted"}]
    )
    assert dec_res.status_code == 200
    assert dec_res.json()["diff"][0]["status"] == "accepted"

    # 5. Commit proposal
    commit_res = client.post(
        f"/v1/sessions/{session_id}/proposals/{proposal_id}/commit",
        json={"commit_message": "Applied New text replacement"}
    )
    assert commit_res.status_code == 200
    assert commit_res.json()["version_num"] == 2

    # 6. List versions
    list_res = client.get(f"/v1/sessions/{session_id}/versions")
    assert list_res.status_code == 200
    versions = list_res.json()
    assert len(versions) == 2
    assert versions[1]["version_num"] == 2
    assert versions[1]["commit_message"] == "Applied New text replacement"

    # 7. Export version 2 and verify content
    export_res = client.get(f"/v1/sessions/{session_id}/versions/2/export")
    assert export_res.status_code == 200
    from app.docx.package import OpcPackage
    exported_pkg = OpcPackage(export_res.content)
    doc_xml = exported_pkg.get_part_content("word/document.xml")
    assert b"New text" in doc_xml
    assert b"inside paragraph." in doc_xml
    assert b"Old text" not in doc_xml
