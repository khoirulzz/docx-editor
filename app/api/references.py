from fastapi import APIRouter
from app.references.intake import process_reference_intake

router = APIRouter(prefix="/sessions/{session_id}/references", tags=["references"])

@router.post("/process", status_code=202)
async def process_references(session_id: str):
    """Trigger reference intake processing."""
    return {"message": "Reference processing started"}

@router.get("/summary")
async def get_reference_summary(session_id: str):
    """Get summary of processed references."""
    return process_reference_intake(session_id, [])
