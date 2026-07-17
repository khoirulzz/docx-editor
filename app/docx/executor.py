import copy
from typing import Any, Dict, List, Optional, Tuple
from lxml import etree
from app.docx.fields import W_NS, W_P, W_R, W_T
from app.docx.anchors import AnchorResolver
from app.models.domain import (
    CitationContentBlock,
    ContentBlock,
    DiffItem,
    DocumentGraph,
    InsertParagraphOperation,
    OperationModel,
    ReplacePlainParagraphOperation,
    ReplaceTextSpanOperation,
    DeletePlainParagraphOperation,
    TextContentBlock,
)
from app.references.csl import CslProcessor
from app.core.errors import PreconditionFailedError

W_PPR = f"{{{W_NS}}}pPr"
W_RPR = f"{{{W_NS}}}rPr"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

class DocxMutationExecutor:
    """
    Deterministic DOCX mutation engine.
    Executes span replacement across mixed runs, paragraph insertions, and preserves run/paragraph styling.
    """
    def __init__(self, root: etree._Element, graph: DocumentGraph, reference_store: Optional[Dict[str, Any]] = None):
        self.root = root
        self.graph = graph
        self.reference_store = reference_store or {}
        self.resolver = AnchorResolver(root, graph)
        self.csl_processor = CslProcessor()
        self.diffs: List[DiffItem] = []

    def execute_operations(self, operations: List[OperationModel]) -> List[DiffItem]:
        self.diffs = []
        for op in operations:
            elem, node = self.resolver.resolve(op.target)
            
            # Check editability gate
            if not node.editability.get("editable", True):
                raise PreconditionFailedError(
                    f"Operation '{op.operation_id}' rejected: Target node '{node.node_id}' is protected. "
                    f"Reason: {node.editability.get('reason')}"
                )

            before_text = AnchorResolver.compute_element_text_hash(elem)  # or full text
            
            if op.type == "replace_text_span":
                assert isinstance(op, ReplaceTextSpanOperation)
                diff = self._execute_replace_span(elem, node, op)
            elif op.type in ("insert_paragraph_before", "insert_paragraph_after"):
                assert isinstance(op, InsertParagraphOperation)
                diff = self._execute_insert_paragraph(elem, node, op)
            elif op.type == "replace_plain_paragraph":
                assert isinstance(op, ReplacePlainParagraphOperation)
                diff = self._execute_replace_paragraph(elem, node, op)
            elif op.type == "delete_plain_paragraph":
                assert isinstance(op, DeletePlainParagraphOperation)
                diff = self._execute_delete_paragraph(elem, node, op)
            else:
                raise PreconditionFailedError(f"Unsupported operation type: {op.type}")

            self.diffs.append(diff)
            
        return self.diffs

    def _render_block_to_runs(self, block: ContentBlock, base_rpr: Optional[etree._Element]) -> List[etree._Element]:
        """Converts a ContentBlock into lxml run elements with styling."""
        if isinstance(block, TextContentBlock) or block.type == "text":
            text_str = block.text
        else:
            assert isinstance(block, CitationContentBlock) or block.type == "citation"
            text_str = self.csl_processor.render_citation_text(block, self.reference_store)

        r_elem = etree.Element(W_R)
        if base_rpr is not None:
            r_elem.append(copy.deepcopy(base_rpr))
        t_elem = etree.SubElement(r_elem, W_T)
        t_elem.text = text_str
        if text_str.startswith(" ") or text_str.endswith(" "):
            t_elem.set(XML_SPACE, "preserve")
        return [r_elem]

    def _execute_replace_span(self, elem: etree._Element, node: Any, op: ReplaceTextSpanOperation) -> DiffItem:
        # 1. Gather all runs and accumulate text with char mappings
        runs = elem.findall(f".//{{{W_NS}}}r")
        full_text_parts = []
        # list of (char_index_in_full_text, run_elem, offset_in_run_text)
        char_map: List[Tuple[etree._Element, int]] = []

        for r in runs:
            t = r.find(f".//{{{W_NS}}}t")
            if t is not None and t.text:
                for idx, ch in enumerate(t.text):
                    char_map.append((r, idx))
                full_text_parts.append(t.text)

        full_text = "".join(full_text_parts)
        start_idx = full_text.find(op.expected_text)
        if start_idx == -1:
            raise PreconditionFailedError(
                f"ReplaceTextSpan '{op.operation_id}' failed: expected_text '{op.expected_text}' not found in target paragraph."
            )

        end_idx = start_idx + len(op.expected_text) - 1  # inclusive

        start_run, start_run_offset = char_map[start_idx]
        end_run, end_run_offset = char_map[end_idx]

        # Determine run style properties to inherit
        base_rpr = start_run.find(W_RPR)
        if base_rpr is None and op.run_style_policy == "inherit_from_end":
            base_rpr = end_run.find(W_RPR)

        # 2. Modify runs
        if start_run is end_run:
            # Substring is entirely within a single run
            t_elem = start_run.find(f".//{{{W_NS}}}t")
            original_run_text = t_elem.text
            prefix = original_run_text[:start_run_offset]
            suffix = original_run_text[end_run_offset + 1:]
            
            # Update start_run text to prefix
            t_elem.text = prefix
            if prefix.startswith(" ") or prefix.endswith(" "):
                t_elem.set(XML_SPACE, "preserve")

            # Create new runs for replacement blocks and insert after start_run
            insert_pos_elem = start_run
            for block in op.replacement_content:
                new_runs = self._render_block_to_runs(block, base_rpr)
                for nr in new_runs:
                    insert_pos_elem.addnext(nr)
                    insert_pos_elem = nr

            # If suffix remains, create a suffix run
            if suffix:
                s_run = etree.Element(W_R)
                if base_rpr is not None:
                    s_run.append(copy.deepcopy(base_rpr))
                st = etree.SubElement(s_run, W_T)
                st.text = suffix
                if suffix.startswith(" ") or suffix.endswith(" "):
                    st.set(XML_SPACE, "preserve")
                insert_pos_elem.addnext(s_run)
        else:
            # Substring spans multiple runs
            t_start = start_run.find(f".//{{{W_NS}}}t")
            t_start.text = t_start.text[:start_run_offset]
            if t_start.text.startswith(" ") or t_start.text.endswith(" "):
                t_start.set(XML_SPACE, "preserve")

            t_end = end_run.find(f".//{{{W_NS}}}t")
            t_end.text = t_end.text[end_run_offset + 1:]
            if t_end.text.startswith(" ") or t_end.text.endswith(" "):
                t_end.set(XML_SPACE, "preserve")

            # Remove all runs strictly between start_run and end_run
            in_between = False
            runs_to_remove = []
            for r in runs:
                if r is start_run:
                    in_between = True
                    continue
                if r is end_run:
                    break
                if in_between:
                    runs_to_remove.append(r)

            for r in runs_to_remove:
                r.getparent().remove(r)

            # Insert replacement runs right after start_run
            insert_pos_elem = start_run
            for block in op.replacement_content:
                new_runs = self._render_block_to_runs(block, base_rpr)
                for nr in new_runs:
                    insert_pos_elem.addnext(nr)
                    insert_pos_elem = nr

        after_text = "".join(t.text for t in elem.findall(f".//{{{W_NS}}}t") if t.text)
        return DiffItem(
            operation_id=op.operation_id,
            target_node_id=op.target.node_id,
            diff_type="replace_text_span",
            before_text=full_text,
            after_text=after_text,
            status="accepted"
        )

    def _execute_insert_paragraph(self, elem: etree._Element, node: Any, op: InsertParagraphOperation) -> DiffItem:
        new_p = etree.Element(W_P)
        
        # Style inheritance
        if op.paragraph_style_policy.inherit_paragraph_style:
            base_ppr = elem.find(W_PPR)
            if base_ppr is not None:
                new_p.append(copy.deepcopy(base_ppr))

        # Render content blocks into runs
        for block in op.content:
            new_runs = self._render_block_to_runs(block, None)
            for nr in new_runs:
                new_p.append(nr)

        if op.type == "insert_paragraph_before":
            elem.addprevious(new_p)
        else:
            elem.addnext(new_p)

        new_text = "".join(t.text for t in new_p.findall(f".//{{{W_NS}}}t") if t.text)
        return DiffItem(
            operation_id=op.operation_id,
            target_node_id=op.target.node_id,
            diff_type=op.type,
            before_text="",
            after_text=new_text,
            status="accepted"
        )

    def _execute_replace_paragraph(self, elem: etree._Element, node: Any, op: ReplacePlainParagraphOperation) -> DiffItem:
        before_text = "".join(t.text for t in elem.findall(f".//{{{W_NS}}}t") if t.text)
        base_ppr = copy.deepcopy(elem.find(W_PPR)) if elem.find(W_PPR) is not None else None
        
        # Clear all existing children (runs, etc.)
        elem.clear()
        if base_ppr is not None:
            elem.append(base_ppr)

        for block in op.replacement_content:
            new_runs = self._render_block_to_runs(block, None)
            for nr in new_runs:
                elem.append(nr)

        after_text = "".join(t.text for t in elem.findall(f".//{{{W_NS}}}t") if t.text)
        return DiffItem(
            operation_id=op.operation_id,
            target_node_id=op.target.node_id,
            diff_type="replace_plain_paragraph",
            before_text=before_text,
            after_text=after_text,
            status="accepted"
        )

    def _execute_delete_paragraph(self, elem: etree._Element, node: Any, op: DeletePlainParagraphOperation) -> DiffItem:
        before_text = "".join(t.text for t in elem.findall(f".//{{{W_NS}}}t") if t.text)
        elem.getparent().remove(elem)
        return DiffItem(
            operation_id=op.operation_id,
            target_node_id=op.target.node_id,
            diff_type="delete_plain_paragraph",
            before_text=before_text,
            after_text="",
            status="accepted"
        )
