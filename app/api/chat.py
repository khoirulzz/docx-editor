from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.models.domain import (
    EditPlan,
    ProposalState,
    SessionState,
)
from app.storage.sessions import session_store
from app.storage.versions import version_store
from app.docx.package import OpcPackage
from app.docx.inspector import DocxInspector
from app.docx.executor import DocxMutationExecutor
from app.docx.serializer import DocxSerializer
from app.verification.pipeline import VerificationPipeline
from app.agents.planner import EditPlannerAgent
from app.agents.verifier import SemanticVerifierAgent, SemanticVerificationReport
from app.api.proposals import ProposalResponse
from app.core.errors import PreconditionFailedError, PlanValidationError, NotFoundError

router = APIRouter(prefix="/sessions", tags=["chat"])

class AgentPlanRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=10000, description="Natural language prompt specifying desired academic edits.")
    explicit_node_ids: Optional[List[str]] = Field(default=None, description="Optional explicit node IDs to restrict scope.")
    explicit_chapter_ids: Optional[List[str]] = Field(default=None, description="Optional explicit chapter IDs to restrict scope.")
    reference_store: Optional[Dict[str, Any]] = Field(default=None, description="Available reference assets.")
    run_semantic_verifier: bool = Field(default=True, description="Whether to run advisory semantic check on generated diffs.")

class AgentPlanResponse(BaseModel):
    plan: EditPlan
    proposal: ProposalResponse
    semantic_verifier_report: Optional[SemanticVerificationReport] = None

@router.post("/{session_id}/chat", response_model=AgentPlanResponse, status_code=status.HTTP_201_CREATED)
def plan_and_create_proposal(session_id: str, req: AgentPlanRequest):
    session = session_store.get_session(session_id)
    if not session:
        raise NotFoundError("Session")

    if session.state not in (SessionState.READY, SessionState.PROPOSAL_READY, SessionState.AWAITING_APPROVAL):
        raise PreconditionFailedError(f"Session is in invalid state for planning: {session.state}")

    current_version_record = version_store.get_version(session_id, session.current_version)
    if not current_version_record:
        raise NotFoundError("Current version")

    original_pkg = OpcPackage(current_version_record.docx_bytes)
    base_inspector = DocxInspector(original_pkg)
    base_graph = base_inspector.build_graph()
    root = original_pkg.get_xml_tree(original_pkg.main_document_part)

    # 1. Invoke EditPlannerAgent to generate and validate EditPlan
    planner = EditPlannerAgent()
    available_ref_ids = list(req.reference_store.keys()) if req.reference_store else []
    references_slice_lines = []
    if req.reference_store:
        for ref_id, ref_meta in req.reference_store.items():
            author = ref_meta.get("author", [{}])
            author_str = ", ".join([a.get("family", a.get("literal", "")) for a in author if isinstance(a, dict)]) or ref_meta.get("title", ref_id)
            title = ref_meta.get("title", "")
            year = ""
            if isinstance(ref_meta.get("issued"), dict) and "date-parts" in ref_meta["issued"] and ref_meta["issued"]["date-parts"]:
                year = str(ref_meta["issued"]["date-parts"][0][0])
            elif "year" in ref_meta:
                year = str(ref_meta["year"])
            references_slice_lines.append(f"{ref_id}: {author_str} - {title} ({year})")
    references_slice = "\n".join(references_slice_lines)

    try:
        plan = planner.plan(
            graph=base_graph,
            instruction=req.instruction,
            explicit_node_ids=req.explicit_node_ids,
            explicit_chapter_ids=req.explicit_chapter_ids,
            available_reference_ids=available_ref_ids,
            references_slice=references_slice
        )
    except PlanValidationError as e:
        raise HTTPException(status_code=422, detail=f"Agent planning failed schema or semantic checks: {str(e)}")

    # Ensure document_id and document_version match active session graph
    plan.document_id = base_graph.document_id
    plan.document_version = base_graph.version

    # Auto-resolve placeholder expected_text_hash from active document graph
    node_map = {n.node_id: n for n in base_graph.nodes}
    for op in plan.operations:
        if getattr(op, "target", None) and op.target.node_id in node_map:
            n = node_map[op.target.node_id]
            if op.target.expected_text_hash in ("sha256:will_be_resolved", "sha256:will_be_calculated", "sha256:resolved", "", None) or not op.target.expected_text_hash.startswith("sha256:"):
                op.target.expected_text_hash = n.text_hash

    # 2. Execute mutations deterministically
    executor = DocxMutationExecutor(root, base_graph, reference_store=req.reference_store)
    try:
        diffs = executor.execute_operations(plan.operations)
    except PreconditionFailedError as e:
        raise HTTPException(status_code=412, detail=str(e))

    # 3. Serialize proposed package
    serializer = DocxSerializer(original_pkg)
    proposal_bytes, _ = serializer.serialize({original_pkg.main_document_part: root})

    # 4. Inspect proposed package
    proposal_pkg = OpcPackage(proposal_bytes)
    proposal_graph = DocxInspector(proposal_pkg).build_graph()

    # 5. Run Verification Pipeline
    pipeline = VerificationPipeline()
    report = pipeline.run_pipeline(proposal_bytes, base_graph, proposal_graph, plan=plan)

    if report.blocking_pass:
        prop_state = ProposalState.AWAITING_APPROVAL
        session.state = SessionState.AWAITING_APPROVAL
    else:
        prop_state = ProposalState.VERIFICATION_FAILED
        session.state = SessionState.VERIFICATION_FAILED
    session_store.save_session(session)

    # 6. Save Proposal Record
    proposal_id = f"prop_{len(version_store.list_proposals(session_id)) + 1}"
    version_store.create_proposal(
        proposal_id=proposal_id,
        session_id=session_id,
        base_version=session.current_version,
        plan=plan,
        diffs=diffs,
        verification_report=report,
        proposal_bytes=proposal_bytes,
        proposal_graph=proposal_graph,
        status=prop_state
    )

    prop_resp = ProposalResponse(
        proposal_id=proposal_id,
        session_id=session_id,
        base_version=session.current_version,
        status=prop_state,
        diff=diffs,
        verification_report=report
    )

    # 7. Optional Semantic Verification
    verifier_report = None
    if req.run_semantic_verifier:
        verifier = SemanticVerifierAgent()
        verifier_report = verifier.verify_proposal(req.instruction, diffs, plan=plan)

    return AgentPlanResponse(
        plan=plan,
        proposal=prop_resp,
        semantic_verifier_report=verifier_report
    )

@router.post("/{session_id}/chat/stream")
def plan_and_create_proposal_stream(session_id: str, req: AgentPlanRequest):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time thinking and tool-call updates.
    """
    import json
    from fastapi.responses import StreamingResponse

    def sse_generator():
        def format_sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            session = session_store.get_session(session_id)
            if not session:
                yield format_sse("error", {"message": "Session not found."})
                return

            if session.state not in (SessionState.READY, SessionState.PROPOSAL_READY, SessionState.AWAITING_APPROVAL):
                yield format_sse("error", {"message": f"Session is in invalid state for planning: {session.state}"})
                return

            current_version_record = version_store.get_version(session_id, session.current_version)
            if not current_version_record:
                yield format_sse("error", {"message": "Current version not found."})
                return

            original_pkg = OpcPackage(current_version_record.docx_bytes)
            base_inspector = DocxInspector(original_pkg)
            base_graph = base_inspector.build_graph()
            root = original_pkg.get_xml_tree(original_pkg.main_document_part)

            # 1. Scope Selection
            yield format_sse("tool_call", {"tool": "ScopeSelector", "status": "running", "message": "Mengkalkulasi ruang lingkup instruksi dan membedah struktur bab..."})
            planner = EditPlannerAgent()
            available_ref_ids = list(req.reference_store.keys()) if req.reference_store else []

            yield format_sse("thinking", {"text": f"Menganalisis instruksi pengguna: \"{req.instruction[:80]}...\". Memilih node dan bab relevan..."})
            
            # Run scope selection explicitly to emit detailed progress
            from app.agents.scope import ScopeSelector, ContextPruner
            selected_node_ids, selected_chapter_ids = ScopeSelector.select_scope(
                graph=base_graph,
                instruction_text=req.instruction,
                explicit_node_ids=req.explicit_node_ids,
                explicit_chapter_ids=req.explicit_chapter_ids
            )
            yield format_sse("thinking", {"text": f"Terpilih {len(selected_node_ids)} paragraf/node terkait di bab {selected_chapter_ids if selected_chapter_ids else '[Seluruh Dokumen]'}. Memformat konteks..."})

            doc_slice = ContextPruner.format_document_slice(
                graph=base_graph,
                allowed_node_ids=selected_node_ids,
                allowed_chapter_ids=selected_chapter_ids
            )

            # 2. Call LLM
            yield format_sse("tool_call", {"tool": "EditPlannerAgent", "status": "running", "message": "Memanggil model Blackbox AI (deepseek-v4-pro) untuk merancang proposal mutasi..."})
            system_prompt = planner.build_system_prompt()
            user_prompt = planner.build_user_prompt(
                instruction=req.instruction,
                document_slice=doc_slice,
                references_slice=""
            )

            raw_json_str = planner.client.generate_plan_json(system_prompt, user_prompt)
            yield format_sse("thinking", {"text": "Respons dari model diterima. Melakukan verifikasi skema dan ekstraksi JSON di PlanGateway..."})

            try:
                plan = planner.gateway.validate_plan(raw_json_str, available_reference_ids=available_ref_ids)
            except PlanValidationError as err:
                yield format_sse("thinking", {"text": f"Pemeriksaan skema menemukan catatan: {str(err)[:120]}. Melakukan 1x automatic repair retry..."})
                repair_json_str = planner.client.repair_plan_json(
                    system_prompt=system_prompt,
                    previous_output=raw_json_str,
                    validation_errors=str(err)
                )
                plan = planner.gateway.validate_plan(repair_json_str, available_reference_ids=available_ref_ids)

            yield format_sse("thinking", {"text": f"Proposal selesai disusun: \"{plan.instruction_summary}\" dengan {len(plan.operations)} operasi mutasi."})

            # Ensure document_id and document_version match active session graph
            plan.document_id = base_graph.document_id
            plan.document_version = base_graph.version

            # Auto-resolve placeholder expected_text_hash from active document graph
            node_map = {n.node_id: n for n in base_graph.nodes}
            for op in plan.operations:
                if getattr(op, "target", None) and op.target.node_id in node_map:
                    n = node_map[op.target.node_id]
                    if op.target.expected_text_hash in ("sha256:will_be_resolved", "sha256:will_be_calculated", "sha256:resolved", "", None) or not op.target.expected_text_hash.startswith("sha256:"):
                        op.target.expected_text_hash = n.text_hash

            # 3. Execute mutations deterministically
            yield format_sse("tool_call", {"tool": "DocxMutationExecutor", "status": "running", "message": f"Mengeksekusi {len(plan.operations)} operasi mutasi secara deterministik pada salinan OPC package..."})
            executor = DocxMutationExecutor(root, base_graph, reference_store=req.reference_store)
            diffs = executor.execute_operations(plan.operations)

            serializer = DocxSerializer(original_pkg)
            proposal_bytes, _ = serializer.serialize({original_pkg.main_document_part: root})

            # 4. Inspect & Verify
            yield format_sse("tool_call", {"tool": "VerificationPipeline", "status": "running", "message": "Menjalankan uji integritas L1 (Package), L2 (XML), L4 (Structure), & L5 (Citation)..."})
            proposal_pkg = OpcPackage(proposal_bytes)
            proposal_graph = DocxInspector(proposal_pkg).build_graph()

            pipeline = VerificationPipeline()
            report = pipeline.run_pipeline(proposal_bytes, base_graph, proposal_graph, plan=plan)

            if report.blocking_pass:
                prop_state = ProposalState.AWAITING_APPROVAL
                session.state = SessionState.AWAITING_APPROVAL
            else:
                prop_state = ProposalState.VERIFICATION_FAILED
                session.state = SessionState.VERIFICATION_FAILED
            session_store.save_session(session)

            proposal_id = f"prop_{len(version_store.list_proposals(session_id)) + 1}"
            version_store.create_proposal(
                proposal_id=proposal_id,
                session_id=session_id,
                base_version=session.current_version,
                plan=plan,
                diffs=diffs,
                verification_report=report,
                proposal_bytes=proposal_bytes,
                proposal_graph=proposal_graph,
                status=prop_state
            )

            prop_resp = ProposalResponse(
                proposal_id=proposal_id,
                session_id=session_id,
                base_version=session.current_version,
                status=prop_state,
                diff=diffs,
                verification_report=report
            )

            verifier_report = None
            if req.run_semantic_verifier:
                yield format_sse("tool_call", {"tool": "SemanticVerifierAgent", "status": "running", "message": "Melakukan pemeriksaan semantik penasihat (Advisory Check)..."})
                verifier = SemanticVerifierAgent()
                verifier_report = verifier.verify_proposal(req.instruction, diffs, plan=plan)

            yield format_sse("proposal_ready", {
                "plan": plan.model_dump(),
                "proposal": prop_resp.model_dump(),
                "semantic_verifier_report": verifier_report.model_dump() if verifier_report else None
            })

        except Exception as e:
            yield format_sse("error", {"message": f"Agent planning or execution failed: {str(e)}"})

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
