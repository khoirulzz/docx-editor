import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.models.domain import DocumentGraph, SessionSummary, SessionState
from app.core.errors import NotFoundError

class SessionRecord:
    def __init__(self, session_id: str, document_id: str, graph: DocumentGraph, raw_bytes: bytes):
        self.session_id = session_id
        self.document_id = document_id
        self.graph = graph
        self.raw_bytes = raw_bytes
        self.current_version = 1
        self.state = SessionState.READY
        self.created_at = datetime.now(timezone.utc)
        self.warnings: list[str] = []

    def to_summary(self) -> SessionSummary:
        return SessionSummary(
            session_id=self.session_id,
            state=self.state,
            document_id=self.document_id,
            current_version=self.current_version,
            outline=self.graph.chapters,
            capabilities=self.graph.capabilities,
            warnings=self.warnings
        )

class SessionStore:
    """InMemory/Local storage for active document sessions and their DocumentGraphs."""
    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}

    def create_session(self, graph: DocumentGraph, raw_bytes: bytes) -> SessionRecord:
        from app.storage.versions import version_store
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        record = SessionRecord(
            session_id=session_id,
            document_id=graph.document_id,
            graph=graph,
            raw_bytes=raw_bytes
        )
        self._sessions[session_id] = record
        version_store.save_version(
            session_id=session_id,
            version=1,
            raw_bytes=raw_bytes,
            graph=graph
        )
        return record

    def update_version(self, session_id: str, new_version: int, new_graph: DocumentGraph, new_bytes: bytes) -> SessionRecord:
        record = self.get_session(session_id)
        record.current_version = new_version
        record.graph = new_graph
        record.raw_bytes = new_bytes
        return record

    def get_session(self, session_id: str) -> SessionRecord:
        if session_id not in self._sessions:
            raise NotFoundError(f"Session '{session_id}'")
        return self._sessions[session_id]

    def delete_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    def save_session(self, record: SessionRecord) -> SessionRecord:
        self._sessions[record.session_id] = record
        return record

    def clear_for_testing(self) -> None:
        self._sessions.clear()

# Global singleton session store for local/development run
session_store = SessionStore()
