import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage.sessions import session_store
from app.storage.versions import version_store
from app.models.domain import SessionState
from tests.test_package_security import create_mock_docx

client = TestClient(app)

def create_sample_docx() -> bytes:
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p><w:r><w:t>BAB I PENDAHULUAN</w:t></w:r></w:p>
            <w:p><w:r><w:t>Latar belakang masalah penelitian DOCX editor.</w:t></w:r></w:p>
        </w:body>
    </w:document>'''
    return create_mock_docx({"word/document.xml": mock_xml})

def test_chat_agent_planning_flow():
    # 1. Create Session
    docx_bytes = create_sample_docx()
    resp_sess = client.post(
        "/v1/sessions",
        files={"file": ("test.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert resp_sess.status_code == 201
    session_id = resp_sess.json()["session_id"]

    # 2. Call /v1/sessions/{session_id}/chat with prompt
    chat_payload = {
        "instruction": "Tolong ubah BAB I PENDAHULUAN menjadi BAB 1 PENDAHULUAN BARU",
        "run_semantic_verifier": True
    }
    resp_chat = client.post(f"/v1/sessions/{session_id}/chat", json=chat_payload)
    assert resp_chat.status_code == 201
    
    data = resp_chat.json()
    assert "plan" in data
    assert "proposal" in data
    assert "semantic_verifier_report" in data
    
    prop = data["proposal"]
    assert prop["session_id"] == session_id
    assert prop["status"] in ("AWAITING_APPROVAL", "VERIFICATION_FAILED")
    assert prop["proposal_id"].startswith("prop_")
    
    # Verify session is now AWAITING_APPROVAL (or VERIFICATION_FAILED)
    session = session_store.get_session(session_id)
    assert session.state == prop["status"]

def test_chat_invalid_session_state():
    docx_bytes = create_sample_docx()
    resp_sess = client.post(
        "/v1/sessions",
        files={"file": ("test.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    session_id = resp_sess.json()["session_id"]

    # Manually set session state to COMMITTED to simulate invalid state for planning
    session = session_store.get_session(session_id)
    session.state = SessionState.COMMITTED
    session_store.save_session(session)

    resp = client.post(
        f"/v1/sessions/{session_id}/chat",
        json={"instruction": "Coba edit lagi"}
    )
    assert resp.status_code == 400
    assert "invalid state" in resp.json()["error"]["message"].lower()

def test_chat_nonexistent_session():
    resp = client.post(
        "/v1/sessions/nonexistent_id/chat",
        json={"instruction": "Hello agent"}
    )
    assert resp.status_code == 404
