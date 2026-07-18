import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage.sessions import session_store
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

def test_chat_stream_flow():
    # 1. Create Session
    docx_bytes = create_sample_docx()
    resp_sess = client.post(
        "/v1/sessions",
        files={"file": ("test.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert resp_sess.status_code == 201
    session_id = resp_sess.json()["session_id"]

    # 2. Call /v1/sessions/{session_id}/chat/stream
    chat_payload = {
        "instruction": "Tolong ubah BAB I PENDAHULUAN menjadi BAB 1 PENDAHULUAN BARU",
        "run_semantic_verifier": False
    }
    with client.stream("POST", f"/v1/sessions/{session_id}/chat/stream", json=chat_payload) as resp_stream:
        assert resp_stream.status_code == 200
        assert "text/event-stream" in resp_stream.headers.get("content-type", "")

        events = []
        buffer = ""
        for line in resp_stream.iter_lines():
            if not line:
                continue
            buffer += line + "\n"
            if line.startswith("data: "):
                # Parse block
                lines = buffer.strip().split("\n")
                ev = "message"
                data_str = ""
                for l in lines:
                    if l.startswith("event: "):
                        ev = l[7:].strip()
                    elif l.startswith("data: "):
                        data_str = l[6:].strip()
                if data_str:
                    try:
                        events.append((ev, json.loads(data_str)))
                    except json.JSONDecodeError:
                        pass
                buffer = ""

    assert len(events) > 0
    event_types = [ev[0] for ev in events]
    assert "tool_call" in event_types
    assert "thinking" in event_types
    assert "proposal_ready" in event_types

    # Find proposal_ready data
    proposal_ready_data = next(ev[1] for ev in events if ev[0] == "proposal_ready")
    assert "plan" in proposal_ready_data
    assert "proposal" in proposal_ready_data
    assert proposal_ready_data["proposal"]["session_id"] == session_id
    assert proposal_ready_data["proposal"]["proposal_id"].startswith("prop_")

def test_chat_stream_not_found():
    chat_payload = {"instruction": "Test"}
    with client.stream("POST", "/v1/sessions/nonexistent_session/chat/stream", json=chat_payload) as resp_stream:
        assert resp_stream.status_code == 200
        events = []
        for line in resp_stream.iter_lines():
            if line.startswith("event: error"):
                events.append("error")
        assert "error" in events
