from typing import Any, Dict, List, Optional
from lxml import etree
from app.models.domain import VerificationLevelResult, VerificationStatus
from app.docx.package import HARDENED_XML_PARSER

class OpenXmlValidator:
    """
    Python-native L3 OpenXML structure & well-formedness verification.
    Runs on Hugging Face Spaces (Linux containers without .NET CLI).
    L3 is optional/best-effort check.
    """
    def __init__(self, schema_path: Optional[str] = None):
        self.schema: Optional[etree.XMLSchema] = None
        if schema_path:
            try:
                with open(schema_path, "rb") as f:
                    schema_doc = etree.fromstring(f.read(), HARDENED_XML_PARSER)
                    self.schema = etree.XMLSchema(schema_doc)
            except Exception as e:
                # Schema file missing or unloadable in minimal container; keep L3 best-effort
                pass

    def validate_xml_part(self, part_name: str, raw_xml: bytes) -> VerificationLevelResult:
        checks: List[Dict[str, Any]] = []
        try:
            doc = etree.fromstring(raw_xml, HARDENED_XML_PARSER)
            checks.append({
                "check": "well_formed_syntax",
                "status": "PASS",
                "detail": f"Part '{part_name}' is well-formed XML."
            })
            
            if self.schema:
                if self.schema.validate(doc):
                    checks.append({
                        "check": "xsd_schema_validation",
                        "status": "PASS",
                        "detail": f"Part '{part_name}' satisfies XSD schema constraints."
                    })
                else:
                    err_msg = str(self.schema.error_log.last_error) if self.schema.error_log else "Schema mismatch."
                    checks.append({
                        "check": "xsd_schema_validation",
                        "status": "WARNING",  # Best-effort / non-blocking as specified
                        "detail": f"Part '{part_name}' XSD note: {err_msg}"
                    })
            else:
                checks.append({
                    "check": "xsd_schema_validation",
                    "status": "NOT_RUN",
                    "detail": "Python-native XSD schema file not mounted; syntax verification passed."
                })

            return VerificationLevelResult(status=VerificationStatus.PASS, checks=checks)
        except Exception as e:
            checks.append({
                "check": "well_formed_syntax",
                "status": "FAIL",
                "detail": f"Part '{part_name}' malformed XML: {str(e)}"
            })
            return VerificationLevelResult(status=VerificationStatus.FAIL, checks=checks)
