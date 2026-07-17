from fastapi import APIRouter, File, UploadFile, status
from app.docx.package import OpcPackage
from app.docx.inspector import DocxInspector
from app.models.domain import DocumentGraph, SessionSummary
from app.storage.sessions import session_store
from app.core.errors import PreconditionFailedError

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", status_code=status.HTTP_201_CREATED, response_model=SessionSummary)
async def create_session(file: UploadFile = File(...)):
    """
    Uploads a DOCX file, inspects security invariants & relationships,
    builds the DocumentGraph, and initializes an active session.
    """
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise PreconditionFailedError("Only .docx files are accepted.")

    content = await file.read()
    pkg = OpcPackage(content, filename=file.filename)
    inspector = DocxInspector(pkg)
    graph = inspector.build_graph()

    record = session_store.create_session(graph, content)
    return record.to_summary()

@router.get("/{session_id}", response_model=SessionSummary)
async def get_session(session_id: str):
    """Retrieves current session summary, including outline and capabilities."""
    record = session_store.get_session(session_id)
    return record.to_summary()

@router.get("/{session_id}/graph", response_model=DocumentGraph)
async def get_session_graph(session_id: str):
    """Retrieves full DocumentGraph containing nodes, locators, and text hashes."""
    record = session_store.get_session(session_id)
    return record.graph

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    """Deletes a session from active storage."""
    session_store.delete_session(session_id)
    return None
