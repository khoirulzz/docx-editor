import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W_FLDCHAR = f"{{{W_NS}}}fldChar"
W_FLDCHAR_TYPE = f"{{{W_NS}}}fldCharType"
W_INSTRTEXT = f"{{{W_NS}}}instrText"
W_FLDSIMPLE = f"{{{W_NS}}}fldSimple"
W_R = f"{{{W_NS}}}r"
W_T = f"{{{W_NS}}}t"
W_P = f"{{{W_NS}}}p"

@dataclass
class FieldInstance:
    field_id: str
    field_type: str
    instruction: str
    fingerprint_sha256: str
    is_protected: bool
    begin_element: Optional[etree._Element] = None
    separate_element: Optional[etree._Element] = None
    end_element: Optional[etree._Element] = None
    elements: List[etree._Element] = field(default_factory=list)

class FieldStateMachine:
    """
    Complex & Simple Field state machine for DOCX inspection.
    Detects nested complex fields (begin -> instrText -> separate -> result -> end)
    and classifies protected zones (such as Mendeley citations/bibliographies).
    """
    def __init__(self):
        self.fields: List[FieldInstance] = []
        self._stack: List[Dict[str, Any]] = []
        self._counter = 0

    def process_element_tree(self, root: etree._Element) -> List[FieldInstance]:
        self.fields = []
        self._stack = []
        self._counter = 0

        # Iterate over all elements in document order
        for elem in root.iter():
            # If element is part of an currently open field, record it in all open fields on stack
            for state_dict in self._stack:
                state_dict["elements"].append(elem)

            # Handle w:fldSimple
            if elem.tag == W_FLDSIMPLE:
                instr = elem.get(f"{{{W_NS}}}instr", "").strip()
                field_id = f"fld_{self._counter}"
                self._counter += 1
                field_type, is_protected = self.classify_instruction(instr)
                fingerprint = self.compute_fingerprint([elem])
                self.fields.append(FieldInstance(
                    field_id=field_id,
                    field_type=field_type,
                    instruction=instr,
                    fingerprint_sha256=fingerprint,
                    is_protected=is_protected,
                    begin_element=elem,
                    separate_element=elem,
                    end_element=elem,
                    elements=[elem]
                ))
                continue

            # Check if this element is w:fldChar or inside a run containing w:fldChar/w:instrText
            if elem.tag == W_FLDCHAR:
                fld_type = elem.get(W_FLDCHAR_TYPE) or elem.get("w:fldCharType")
                if not fld_type and f"{{{W_NS}}}fldCharType" in elem.attrib:
                    fld_type = elem.attrib[f"{{{W_NS}}}fldCharType"]

                if fld_type == "begin":
                    self._stack.append({
                        "begin_element": elem,
                        "separate_element": None,
                        "instr_parts": [],
                        "elements": [elem]
                    })
                elif fld_type == "separate":
                    if self._stack:
                        self._stack[-1]["separate_element"] = elem
                elif fld_type == "end":
                    if self._stack:
                        top = self._stack.pop()
                        top["elements"].append(elem)
                        instr = "".join(top["instr_parts"]).strip()
                        field_id = f"fld_{self._counter}"
                        self._counter += 1
                        field_type, is_protected = self.classify_instruction(instr)
                        fingerprint = self.compute_fingerprint(top["elements"])
                        self.fields.append(FieldInstance(
                            field_id=field_id,
                            field_type=field_type,
                            instruction=instr,
                            fingerprint_sha256=fingerprint,
                            is_protected=is_protected,
                            begin_element=top["begin_element"],
                            separate_element=top["separate_element"],
                            end_element=elem,
                            elements=top["elements"]
                        ))

            elif elem.tag == W_INSTRTEXT:
                text = elem.text or ""
                for state_dict in self._stack:
                    state_dict["instr_parts"].append(text)

        return self.fields

    @classmethod
    def classify_instruction(cls, instruction: str) -> tuple[str, bool]:
        """Classifies instruction string into field_type and is_protected flag."""
        upper = instruction.upper()
        
        # Mendeley Legacy / Modern Citation & Bibliography protection
        if "ADDIN MENDELEY CITATION" in upper or "CSL_CITATION" in upper:
            return "mendeley_legacy_citation", True
        if "ADDIN MENDELEY BIBLIOGRAPHY" in upper or "CSL_BIBLIOGRAPHY" in upper:
            return "mendeley_legacy_bibliography", True
        if "ADDIN ZOTERO_ITEM" in upper or "ADDIN ZOTERO_BIBL" in upper:
            return "zotero_citation", True
            
        # Table of Contents / Index protection
        if upper.startswith("TOC") or upper.startswith("INDEX"):
            return "table_of_contents", True
            
        # Standard system fields
        if upper.startswith("PAGE") or upper.startswith("NUMPAGES"):
            return "page_number", False
        if upper.startswith("REF ") or upper.startswith("PAGEREF "):
            return "cross_reference", False
        if upper.startswith("HYPERLINK "):
            return "hyperlink", False
            
        # Default fallback: mark unknown complex fields as protected to prevent accidental mutation
        return "other_field", True

    @classmethod
    def compute_fingerprint(cls, elements: List[etree._Element]) -> str:
        """Computes deterministic SHA-256 fingerprint of the field subtree representation."""
        hasher = hashlib.sha256()
        for elem in elements:
            # Hash canonical tag and text/attributes to detect any mutation or tampering
            chunk = f"{elem.tag}|{sorted(elem.attrib.items())}|{elem.text or ''}|{elem.tail or ''}"
            hasher.update(chunk.encode("utf-8"))
        return f"sha256:{hasher.hexdigest()}"
