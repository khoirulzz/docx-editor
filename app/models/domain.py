from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, conlist

# --- Common / Enums ---

class SessionState(str, Enum):
    UPLOADING = "UPLOADING"
    INSPECTING = "INSPECTING"
    READY = "READY"
    PLANNING = "PLANNING"
    PROPOSAL_READY = "PROPOSAL_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    COMMITTED = "COMMITTED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"

class ProposalState(str, Enum):
    PLANNING = "PLANNING"
    PLAN_REJECTED = "PLAN_REJECTED"
    PROPOSAL_READY = "PROPOSAL_READY"
    VERIFYING = "VERIFYING"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class CitationMode(str, Enum):
    AUTO = "auto"
    PRESERVE_ONLY = "preserve_only"
    FORMATTED_CSL = "formatted_csl"
    PLACEHOLDER_MANIFEST = "placeholder_manifest"
    NATIVE_MENDELEY = "native_mendeley"

class NodeType(str, Enum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    ROW = "row"
    CELL = "cell"
    CONTENT_CONTROL = "content_control"

class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_RUN = "not_run"

# --- API Summary Models ---

class SessionSummary(BaseModel):
    session_id: str
    state: SessionState
    document_id: str
    current_version: int = Field(ge=1)
    outline: List[Dict[str, Any]] = Field(default_factory=list)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

class DiffItem(BaseModel):
    operation_id: str
    target_node_id: str
    diff_type: str
    before_text: Optional[str] = None
    after_text: Optional[str] = None
    status: str = "pending"  # pending, accepted, rejected

class ProposalSummary(BaseModel):
    proposal_id: str
    state: ProposalState
    base_version: int = Field(ge=1)
    instruction_summary: str
    operations: List[Dict[str, Any]] = Field(default_factory=list)
    diff: List[Dict[str, Any]] = Field(default_factory=list)
    citation_report: Dict[str, Any] = Field(default_factory=dict)
    verification: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)

# --- DocumentGraph Schema Models ---

class NodeModel(BaseModel):
    node_id: str
    node_type: NodeType
    story_id: str
    ordinal: int
    para_id: Optional[str] = None
    locator: Dict[str, Any] = Field(default_factory=dict)
    text: str
    text_hash: str
    style_id: Optional[str] = None
    outline_level: Optional[int] = None
    parent_node_id: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    editability: Dict[str, Any] = Field(default_factory=dict)

class DocumentGraph(BaseModel):
    schema_version: Literal["document-graph/1.0"] = "document-graph/1.0"
    document_id: str
    version: int = Field(ge=1)
    package_sha256: str
    nodes: List[NodeModel] = Field(default_factory=list)
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    chapters: List[Dict[str, Any]] = Field(default_factory=list)
    capabilities: Dict[str, Any] = Field(default_factory=dict)

# --- EditPlan Schema Models ---

class TargetLocator(BaseModel):
    node_id: str
    expected_text_hash: str = "sha256:will_be_resolved"

class CitationLocator(BaseModel):
    label: Literal["page", "chapter", "section", "paragraph", "line", "figure", "table", "other"]
    value: str

class CitationContentBlock(BaseModel):
    type: Literal["citation"] = "citation"
    reference_ids: List[str] = Field(min_length=1, max_length=20)
    evidence_ids: List[str] = Field(min_length=1, max_length=50)
    citation_mode: Literal["parenthetical", "narrative", "suppress_author"]
    locator: Optional[CitationLocator] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None

class TextContentBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str

ContentBlock = Union[TextContentBlock, CitationContentBlock]

class BaseOperation(BaseModel):
    operation_id: str = "op_default"
    type: str
    group_id: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)
    target: TargetLocator

class InsertParagraphPolicy(BaseModel):
    inherit_paragraph_style: bool = True
    same_list_level: bool = False
    style_id: Optional[str] = "Normal"

class InsertParagraphOperation(BaseOperation):
    type: Literal["insert_paragraph_before", "insert_paragraph_after"]
    content: List[ContentBlock] = Field(min_length=1)
    paragraph_style_policy: InsertParagraphPolicy = Field(default_factory=InsertParagraphPolicy)

class ReplaceTextSpanOperation(BaseOperation):
    type: Literal["replace_text_span"] = "replace_text_span"
    expected_text: str = ""
    replacement_content: List[ContentBlock] = Field(min_length=1)
    run_style_policy: Literal["inherit_from_start", "inherit_from_end", "explicit_token"] = "inherit_from_start"

class ReplacePlainParagraphOperation(BaseOperation):
    type: Literal["replace_plain_paragraph"] = "replace_plain_paragraph"
    expected_text: str = ""
    replacement_content: List[ContentBlock] = Field(min_length=1)
    paragraph_style_policy: InsertParagraphPolicy = Field(default_factory=InsertParagraphPolicy)

class DeletePlainParagraphOperation(BaseOperation):
    type: Literal["delete_plain_paragraph"] = "delete_plain_paragraph"
    expected_text: str = ""

class SetParagraphStyleOperation(BaseOperation):
    type: Literal["set_paragraph_style"] = "set_paragraph_style"
    expected_text: str = ""
    style_id: str = "Normal"

OperationModel = Union[
    InsertParagraphOperation,
    ReplaceTextSpanOperation,
    ReplacePlainParagraphOperation,
    DeletePlainParagraphOperation,
    SetParagraphStyleOperation
]

class EditPlanScope(BaseModel):
    allowed_node_ids: List[str] = Field(default_factory=list)
    chapter_ids: Optional[List[str]] = None

class UnsupportedClaim(BaseModel):
    claim: str
    reason: str

class EditPlan(BaseModel):
    schema_version: Literal["edit-plan/1.0"] = "edit-plan/1.0"
    document_id: str = "doc_default"
    document_version: int = Field(default=1, ge=1)
    instruction_summary: str = "Modification"
    scope: EditPlanScope = Field(default_factory=EditPlanScope)
    operations: List[OperationModel] = Field(default_factory=list, max_length=100)
    used_reference_ids: List[str] = Field(default_factory=list)
    used_evidence_ids: List[str] = Field(default_factory=list)
    unsupported_claims: List[UnsupportedClaim] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)

# --- VerificationReport Schema Models ---

class VerificationLevelResult(BaseModel):
    status: VerificationStatus
    checks: List[Dict[str, Any]] = Field(default_factory=list)

class VerificationLevels(BaseModel):
    package: VerificationLevelResult
    xml: VerificationLevelResult
    openxml_schema: VerificationLevelResult
    structural: VerificationLevelResult
    citations: VerificationLevelResult
    semantic: VerificationLevelResult

class VerificationReport(BaseModel):
    schema_version: Literal["verification-report/1.0"] = "verification-report/1.0"
    blocking_pass: bool
    levels: VerificationLevels
    changed_parts: List[str] = Field(default_factory=list)
    operation_results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
