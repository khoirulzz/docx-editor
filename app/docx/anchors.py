import hashlib
from typing import Optional, Tuple
from lxml import etree
from app.docx.fields import W_NS, W_P, W_T
from app.docx.inspector import W14_PARA_ID
from app.models.domain import DocumentGraph, NodeModel, TargetLocator
from app.core.errors import PreconditionFailedError, NotFoundError

class AnchorResolver:
    """
    Resolves TargetLocator (node_id + expected_text_hash) to live lxml Element in document tree.
    Enforces strict precondition hash matching to prevent stale edits.
    """
    def __init__(self, root: etree._Element, graph: DocumentGraph):
        self.root = root
        self.graph = graph
        self._node_map = {n.node_id: n for n in graph.nodes}

    @staticmethod
    def compute_element_text_hash(elem: etree._Element) -> str:
        """Computes visible/structural text hash of an lxml element (`w:p` or `w:tbl`)."""
        text_parts = []
        for descendant in elem.iter():
            if descendant.tag == W_T and descendant.text:
                text_parts.append(descendant.text)
        text = "".join(text_parts)
        return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    def resolve(self, target: TargetLocator) -> Tuple[etree._Element, NodeModel]:
        """
        Locates target element. Throws PreconditionFailedError if expected_text_hash mismatched
        or NotFoundError if node cannot be located.
        """
        if target.node_id not in self._node_map:
            raise NotFoundError(f"Node ID '{target.node_id}' in graph.")
        
        node = self._node_map[target.node_id]
        elem: Optional[etree._Element] = None

        # 1. Primary lookup via w14:paraId if available
        if node.para_id:
            elem = self._find_by_para_id(node.para_id)

        # 2. Fallback lookup via ordinal index if w14:paraId missing or not matched
        if elem is None:
            elem = self._find_by_ordinal(node)

        # 3. Fallback lookup via unique text hash search if ordinal shifted
        if elem is None:
            elem = self._find_by_unique_hash(target.expected_text_hash)

        if elem is None:
            raise NotFoundError(f"Element corresponding to target node '{target.node_id}'")

        # 4. Strict Precondition Check
        if target.expected_text_hash in ("sha256:will_be_resolved", "sha256:will_be_calculated", "sha256:resolved", "", None) or (target.expected_text_hash and not target.expected_text_hash.startswith("sha256:")):
            if node.text_hash:
                target.expected_text_hash = node.text_hash

        live_hash = self.compute_element_text_hash(elem)
        if live_hash != target.expected_text_hash:
            raise PreconditionFailedError(
                f"Target node '{target.node_id}' text hash mismatch after planning. "
                f"Expected {target.expected_text_hash}, got {live_hash}.",
                details={
                    "node_id": target.node_id,
                    "expected_hash": target.expected_text_hash,
                    "live_hash": live_hash
                }
            )

        return elem, node

    def _find_by_para_id(self, para_id: str) -> Optional[etree._Element]:
        # Search all w:p and w:tbl for matching w14:paraId
        for elem in self.root.iter(W_P, f"{{{W_NS}}}tbl"):
            pid = elem.get(W14_PARA_ID) or elem.get("w14:paraId")
            if pid == para_id:
                return elem
        return None

    def _find_by_ordinal(self, node: NodeModel) -> Optional[etree._Element]:
        body = self.root.find(f".//{{{W_NS}}}body")
        if body is None:
            body = self.root

        target_tag = W_P if node.node_type == "paragraph" else f"{{{W_NS}}}tbl"
        current_ordinal = 0
        for child in body:
            if child.tag == target_tag:
                if current_ordinal == node.ordinal:
                    return child
                current_ordinal += 1
        return None

    def _find_by_unique_hash(self, target_hash: str) -> Optional[etree._Element]:
        matches = []
        for elem in self.root.iter(W_P, f"{{{W_NS}}}tbl"):
            if self.compute_element_text_hash(elem) == target_hash:
                matches.append(elem)
        if len(matches) == 1:
            return matches[0]
        return None
