import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from lxml import etree
from app.docx.fields import FieldInstance, FieldStateMachine, W_NS, W_P, W_T
from app.docx.package import OpcPackage
from app.models.domain import DocumentGraph, NodeModel, NodeType

W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
W_PPR = f"{{{W_NS}}}pPr"
W_PSTYLE = f"{{{W_NS}}}pStyle"
W_VAL = f"{{{W_NS}}}val"
W_TBL = f"{{{W_NS}}}tbl"
W_TR = f"{{{W_NS}}}tr"
W_TC = f"{{{W_NS}}}tc"
W14_PARA_ID = f"{{{W14_NS}}}paraId"

class IndonesianChapterDetector:
    """Detects academic chapter outlines (BAB I/II/III, PENDAHULUAN, etc.) and assigns levels."""
    
    CHAPTER_REGEX = re.compile(
        r"^(?:BAB\s+(?:[IVXLCDM]+|\d+)(?:\s*[:\-.]?\s*(.*))?|PENDAHULUAN|TINJAUAN\s+PUSTAKA|METODE\s+PENELITIAN|HASIL\s+DAN\s+PEMBAHASAN|PEMBAHASAN|METODE|HASIL|SARAN|PENUTUP|KESIMPULAN|DAFTAR\s+PUSTAKA|ABSTRAK|ABSTRACT|KATA\s+PENGANTAR|DAFTAR\s+ISI)",
        re.IGNORECASE
    )
    SUBSECTION_REGEX = re.compile(r"^(\d+\.\d+(?:\.\d+)?|[A-Z]\.)\s+(.+)")

    @classmethod
    def detect_level(cls, text: str, style_id: Optional[str] = None) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Returns (outline_level, chapter_id, title) if detected.
        Level 1 = Chapter / BAB
        Level 2 = Subsection (1.1, A.)
        """
        clean_text = text.strip()
        if not clean_text:
            return None, None, None

        # Check style override
        if style_id:
            lower_style = style_id.lower()
            if lower_style in ("heading1", "judul1", "heading 1"):
                # If text matches chapter pattern, format cleanly
                match = cls.CHAPTER_REGEX.match(clean_text)
                title = clean_text if not match or not match.group(1) else f"BAB - {match.group(1)}"
                return 1, f"chap_{hashlib.md5(clean_text.encode('utf-8')).hexdigest()[:8]}", clean_text
            elif lower_style in ("heading2", "judul2", "heading 2"):
                return 2, None, clean_text
            elif lower_style in ("heading3", "judul3", "heading 3"):
                return 3, None, clean_text

        # Pattern matching for Indonesian chapters
        match = cls.CHAPTER_REGEX.match(clean_text)
        if match:
            # If line is short enough (e.g. < 150 chars) and looks like a title
            if len(clean_text) < 150:
                chap_id = f"chap_{hashlib.md5(clean_text.encode('utf-8')).hexdigest()[:8]}"
                return 1, chap_id, clean_text

        sub_match = cls.SUBSECTION_REGEX.match(clean_text)
        if sub_match and len(clean_text) < 150:
            return 2, None, clean_text

        return None, None, None

class DocxInspector:
    """Inspects DOCX structure, classifies nodes, maps protected zones, and builds DocumentGraph."""
    def __init__(self, package: OpcPackage):
        self.package = package
        self.root = package.get_xml_tree(package.main_document_part)
        self.fields: List[FieldInstance] = []
        self.nodes: List[NodeModel] = []
        self.chapters: List[Dict[str, Any]] = []

    def build_graph(self) -> DocumentGraph:
        # 1. Run FieldStateMachine to discover fields & protected zones
        fsm = FieldStateMachine()
        self.fields = fsm.process_element_tree(self.root)

        # Map protected field elements to protected reasons
        protected_elem_set: Dict[int, str] = {}
        for fld in self.fields:
            if fld.is_protected:
                for elem in fld.elements:
                    protected_elem_set[id(elem)] = fld.field_type

        # 2. Extract block nodes (paragraphs & tables)
        self.nodes = []
        self.chapters = []
        story_id = "main"
        ordinal = 0
        current_chapter_id: Optional[str] = None

        body = self.root.find(f".//{{{W_NS}}}body")
        if body is None:
            body = self.root

        for child in body:
            if child.tag == W_P:
                node = self._process_paragraph(child, story_id, ordinal, protected_elem_set, current_chapter_id)
                self.nodes.append(node)
                ordinal += 1
                if node.outline_level == 1 and node.features.get("chapter_id"):
                    current_chapter_id = node.features["chapter_id"]
                    self.chapters.append({
                        "chapter_id": current_chapter_id,
                        "node_id": node.node_id,
                        "title": node.features.get("title", node.text),
                        "ordinal": len(self.chapters) + 1
                    })

            elif child.tag == W_TBL:
                node = self._process_table(child, story_id, ordinal, protected_elem_set, current_chapter_id)
                self.nodes.append(node)
                ordinal += 1

        # Serialize fields summary for graph
        field_summaries = [
            {
                "field_id": f.field_id,
                "field_type": f.field_type,
                "is_protected": f.is_protected,
                "fingerprint_sha256": f.fingerprint_sha256
            }
            for f in self.fields
        ]

        return DocumentGraph(
            document_id=f"doc_{self.package.package_sha256[:12]}",
            version=1,
            package_sha256=self.package.package_sha256,
            nodes=self.nodes,
            fields=field_summaries,
            chapters=self.chapters,
            capabilities={
                "has_mendeley_citations": any(f.field_type == "mendeley_legacy_citation" for f in self.fields),
                "has_tables": any(n.node_type == NodeType.TABLE for n in self.nodes),
                "total_paragraphs": sum(1 for n in self.nodes if n.node_type == NodeType.PARAGRAPH)
            }
        )

    def _process_paragraph(
        self,
        elem: etree._Element,
        story_id: str,
        ordinal: int,
        protected_elem_set: Dict[int, str],
        current_chapter_id: Optional[str]
    ) -> NodeModel:
        node_id = f"para_{ordinal}"
        para_id = elem.get(W14_PARA_ID) or elem.get("w14:paraId")
        
        # Extract style
        style_id = None
        ppr = elem.find(W_PPR)
        if ppr is not None:
            pstyle = ppr.find(W_PSTYLE)
            if pstyle is not None:
                style_id = pstyle.get(W_VAL)

        # Extract visible text
        text_parts = []
        is_node_protected = False
        protected_reasons = set()

        for descendant in elem.iter():
            if id(descendant) in protected_elem_set:
                is_node_protected = True
                protected_reasons.add(protected_elem_set[id(descendant)])
            if descendant.tag == W_T and descendant.text:
                text_parts.append(descendant.text)

        text = "".join(text_parts)
        text_hash = f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

        # Check outline / Indonesian chapter level
        outline_level, chap_id, chap_title = IndonesianChapterDetector.detect_level(text, style_id)

        features: Dict[str, Any] = {}
        if outline_level:
            features["title"] = chap_title or text
            if chap_id:
                features["chapter_id"] = chap_id

        editability: Dict[str, Any] = {"editable": not is_node_protected}
        if is_node_protected:
            editability["reason"] = f"Contains protected field: {', '.join(protected_reasons)}"

        locator = {"para_id": para_id} if para_id else {"ordinal": ordinal}
        parent_id = chap_id if (outline_level == 1 and chap_id) else current_chapter_id

        return NodeModel(
            node_id=node_id,
            node_type=NodeType.PARAGRAPH,
            story_id=story_id,
            ordinal=ordinal,
            para_id=para_id,
            locator=locator,
            text=text,
            text_hash=text_hash,
            style_id=style_id,
            outline_level=outline_level,
            parent_node_id=parent_id,
            features=features,
            editability=editability
        )

    def _process_table(
        self,
        elem: etree._Element,
        story_id: str,
        ordinal: int,
        protected_elem_set: Dict[int, str],
        current_chapter_id: Optional[str]
    ) -> NodeModel:
        node_id = f"tbl_{ordinal}"
        
        # Extract text summary inside table
        text_parts = []
        is_node_protected = False
        protected_reasons = set()

        for descendant in elem.iter():
            if id(descendant) in protected_elem_set:
                is_node_protected = True
                protected_reasons.add(protected_elem_set[id(descendant)])
            if descendant.tag == W_T and descendant.text:
                text_parts.append(descendant.text)

        text = "".join(text_parts)
        text_hash = f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

        editability: Dict[str, Any] = {"editable": not is_node_protected}
        if is_node_protected:
            editability["reason"] = f"Contains protected field: {', '.join(protected_reasons)}"

        return NodeModel(
            node_id=node_id,
            node_type=NodeType.TABLE,
            story_id=story_id,
            ordinal=ordinal,
            locator={"ordinal": ordinal},
            text=text,
            text_hash=text_hash,
            parent_node_id=current_chapter_id,
            features={"rows_count": len(elem.findall(f".//{{{W_NS}}}tr"))},
            editability=editability
        )
