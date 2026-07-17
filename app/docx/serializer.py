import hashlib
import io
import zipfile
from typing import Dict, Tuple, Union
from lxml import etree
from app.docx.package import OpcPackage

class DocxSerializer:
    """
    Serializes modified DOCX package by repacking modified parts and preserving
    all untouched ZIP entries byte-for-byte.
    """
    def __init__(self, original_pkg: OpcPackage):
        self.original_pkg = original_pkg

    def serialize(self, mutated_parts: Dict[str, Union[bytes, etree._Element]]) -> Tuple[bytes, str]:
        """
        Returns (proposal_docx_bytes, proposal_sha256).
        `mutated_parts` maps ZIP entry names (e.g., 'word/document.xml') to bytes or lxml tree elements.
        """
        out_stream = io.BytesIO()
        with zipfile.ZipFile(out_stream, "w", compression=zipfile.ZIP_DEFLATED) as out_zip:
            for entry_name in self.original_pkg.entries.keys():
                if entry_name in mutated_parts:
                    content = mutated_parts[entry_name]
                    if isinstance(content, etree._Element):
                        data = etree.tostring(content, encoding="utf-8", xml_declaration=True)
                    else:
                        data = content
                    out_zip.writestr(entry_name, data)
                else:
                    # Preserve exact bytes of untouched entries
                    raw_data = self.original_pkg.get_part_content(entry_name)
                    out_zip.writestr(entry_name, raw_data)

        proposal_bytes = out_stream.getvalue()
        proposal_sha256 = f"sha256:{hashlib.sha256(proposal_bytes).hexdigest()}"
        return proposal_bytes, proposal_sha256
