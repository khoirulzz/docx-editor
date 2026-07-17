import pytest
from fastapi.testclient import TestClient
from app.core.errors import PreconditionFailedError
from app.core.plan_gateway import PlanGateway
from app.models.domain import EditPlan

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"

def test_session_upload_and_get_endpoints(client: TestClient):
    from tests.test_package_security import create_mock_docx
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body><w:p><w:r><w:t>BAB I PENDAHULUAN</w:t></w:r></w:p></w:body>
    </w:document>'''
    docx_bytes = create_mock_docx({"word/document.xml": mock_xml})

    # POST /v1/sessions
    resp = client.post(
        "/v1/sessions",
        files={"file": ("test_doc.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["session_id"].startswith("sess_")
    assert data["state"] == "READY"
    assert len(data["outline"]) == 1
    assert data["outline"][0]["title"] == "BAB I PENDAHULUAN"

    session_id = data["session_id"]

    # GET /v1/sessions/{session_id}
    resp = client.get(f"/v1/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id

    # GET /v1/sessions/{session_id}/graph
    resp = client.get(f"/v1/sessions/{session_id}/graph")
    assert resp.status_code == 200
    graph_data = resp.json()
    assert graph_data["schema_version"] == "document-graph/1.0"
    assert len(graph_data["nodes"]) == 1

def test_error_envelope_format(client: TestClient):
    # Route that triggers custom error or test via client
    from app.main import app
    @app.get("/test-error")
    def trigger_error():
        raise PreconditionFailedError("Target paragraph changed.", details={"node_id": "para_1"})

    resp = client.get("/test-error")
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "PRECONDITION_FAILED"
    assert data["error"]["message"] == "Target paragraph changed."
    assert data["error"]["details"] == {"node_id": "para_1"}
    assert "request_id" in data["error"]

def test_plan_gateway_validation():
    gateway = PlanGateway()
    valid_plan_json = {
        "schema_version": "edit-plan/1.0",
        "document_id": "doc_123",
        "document_version": 1,
        "instruction_summary": "Test edit",
        "scope": {"allowed_node_ids": ["n1"]},
        "operations": [],
        "used_reference_ids": ["REF-1"],
        "used_evidence_ids": [],
        "unsupported_claims": [],
        "warnings": [],
        "assumptions": []
    }
    plan = gateway.validate_plan(valid_plan_json, available_reference_ids=["REF-1", "REF-2"])
    assert isinstance(plan, EditPlan)
    assert plan.document_id == "doc_123"

def test_reject_hallucinated_references():
    gateway = PlanGateway()
    invalid_plan_json = {
        "schema_version": "edit-plan/1.0",
        "document_id": "doc_123",
        "document_version": 1,
        "instruction_summary": "Test edit",
        "scope": {"allowed_node_ids": ["n1"]},
        "operations": [],
        "used_reference_ids": ["REF-999"],  # Hallucinated ID
        "used_evidence_ids": [],
        "unsupported_claims": [],
        "warnings": [],
        "assumptions": []
    }
    from app.core.errors import PlanValidationError
    with pytest.raises(PlanValidationError) as exc_info:
        gateway.validate_plan(invalid_plan_json, available_reference_ids=["REF-1"])
    assert "Hallucinated reference ID: REF-999" in str(exc_info.value)
