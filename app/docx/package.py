import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from lxml import etree
from app.core.config import settings
from app.core.errors import ArchiveLimitExceededError, PreconditionFailedError, SecurityViolationError
from app.core.security import normalize_and_validate_zip_entry_path

# Hardened XML parser configured per security requirements
HARDENED_XML_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    dtd_validation=False,
    huge_tree=False,
    remove_blank_text=False,
    recover=False,
)

# OPC Relationship namespaces
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
OFFICE_DOC_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"

@dataclass
class OpcRelationship:
    rel_id: str
    rel_type: str
    target: str
    target_mode: str  # "Internal" or "External"

@dataclass
class PackageEntryInfo:
    normalized_path: str
    compressed_size: int
    uncompressed_size: int
    sha256_hash: str
    content_type: Optional[str] = None
    is_external: bool = False

class OpcPackage:
    """
    Safe OPC/ZIP reader and inventory manager.
    Validates ZIP security constraints (zip bombs, traversal, XXE, duplicate entries)
    and discovers parts via relationships without mutating source.
    """
    def __init__(self, raw_bytes: bytes, filename: str = "document.docx"):
        self.raw_bytes = raw_bytes
        self.filename = filename
        self.package_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        self.entries: Dict[str, PackageEntryInfo] = {}
        self.raw_parts: Dict[str, bytes] = {}
        self.relationships: Dict[str, List[OpcRelationship]] = {}  # source_part -> relationships
        self.content_types: Dict[str, str] = {}  # part_path -> content_type
        self.main_document_part: str = "word/document.xml"  # Resolved via relationships
        
        self._validate_and_inventory()

    def _validate_and_inventory(self) -> None:
        # 0. Size check
        if len(self.raw_bytes) > settings.MAX_UPLOAD_BYTES:
            raise ArchiveLimitExceededError(
                f"File size {len(self.raw_bytes)} bytes exceeds limit of {settings.MAX_UPLOAD_BYTES} bytes."
            )

        if not zipfile.is_zipfile(io.BytesIO(self.raw_bytes)):
            raise SecurityViolationError("File is not a valid ZIP/DOCX archive.")

        with zipfile.ZipFile(io.BytesIO(self.raw_bytes), "r") as zf:
            infolist = zf.infolist()
            
            # 1. Check entry count
            if len(infolist) > settings.MAX_ZIP_ENTRIES:
                raise ArchiveLimitExceededError(
                    f"Archive contains {len(infolist)} entries, exceeding limit of {settings.MAX_ZIP_ENTRIES}."
                )

            seen_paths: Set[str] = set()
            total_uncompressed = 0

            for zinfo in infolist:
                # Reject encrypted entries
                if zinfo.flag_bits & 0x1:
                    raise SecurityViolationError(f"Encrypted ZIP entry rejected: {zinfo.filename}")

                # Normalize and validate path traversal / dangerous patterns
                norm_path = normalize_and_validate_zip_entry_path(zinfo.filename)
                
                # Reject duplicate normalized names
                if norm_path in seen_paths:
                    raise SecurityViolationError(f"Duplicate normalized ZIP entry name: {norm_path}")
                seen_paths.add(norm_path)

                # Check individual entry size
                if zinfo.file_size > settings.MAX_XML_PART_BYTES:
                    raise ArchiveLimitExceededError(
                        f"Entry '{norm_path}' uncompressed size {zinfo.file_size} exceeds limit of {settings.MAX_XML_PART_BYTES} bytes."
                    )

                # Check compression ratio (Zip Bomb protection)
                if zinfo.compress_size > 0:
                    ratio = zinfo.file_size / zinfo.compress_size
                    if ratio > settings.MAX_COMPRESSION_RATIO:
                        raise ArchiveLimitExceededError(
                            f"Compression ratio {ratio:.1f} for entry '{norm_path}' exceeds safety threshold of {settings.MAX_COMPRESSION_RATIO}."
                        )

                total_uncompressed += zinfo.file_size
                if total_uncompressed > settings.MAX_UNCOMPRESSED_BYTES:
                    raise ArchiveLimitExceededError(
                        f"Total uncompressed archive size exceeds limit of {settings.MAX_UNCOMPRESSED_BYTES} bytes."
                    )

                # Read entry bytes into memory safely
                entry_bytes = zf.read(zinfo)
                entry_sha256 = hashlib.sha256(entry_bytes).hexdigest()
                
                self.raw_parts[norm_path] = entry_bytes
                self.entries[norm_path] = PackageEntryInfo(
                    normalized_path=norm_path,
                    compressed_size=zinfo.compress_size,
                    uncompressed_size=zinfo.file_size,
                    sha256_hash=entry_sha256,
                )

        # 2. Check required core parts
        if "[Content_Types].xml" not in self.entries:
            raise SecurityViolationError("Missing required part: [Content_Types].xml")
        if "_rels/.rels" not in self.entries:
            raise SecurityViolationError("Missing required relationship part: _rels/.rels")

        # 3. Parse Content Types and Relationships
        self._parse_content_types()
        self._parse_relationships("_rels/.rels", "/")
        
        # 4. Resolve main document part from root relationships
        root_rels = self.relationships.get("/", [])
        main_rel = next((r for r in root_rels if r.rel_type == OFFICE_DOC_REL_TYPE), None)
        if not main_rel:
            raise PreconditionFailedError("Archive missing valid officeDocument relationship.")
        
        # Normalize target path relative to root
        target_path = main_rel.target.lstrip("/")
        if target_path not in self.entries:
            raise PreconditionFailedError(f"Resolved officeDocument part '{target_path}' does not exist in archive.")
        
        self.main_document_part = target_path
        
        # Parse main document part relationships if they exist
        main_rels_path = self._get_rels_path_for_part(self.main_document_part)
        if main_rels_path in self.entries:
            self._parse_relationships(main_rels_path, self.main_document_part)

    def _parse_content_types(self) -> None:
        raw = self.raw_parts["[Content_Types].xml"]
        if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
            raise SecurityViolationError("[Content_Types].xml contains forbidden DTD/Entity declaration.")
        try:
            tree = etree.fromstring(raw, HARDENED_XML_PARSER)
        except etree.XMLSyntaxError as e:
            raise SecurityViolationError(f"Malformed [Content_Types].xml: {e}")
            
        for child in tree:
            tag = etree.QName(child).localname
            if tag == "Default":
                ext = child.get("Extension", "").lower()
                ctype = child.get("ContentType", "")
                # Store defaults if needed
            elif tag == "Override":
                part_name = child.get("PartName", "").lstrip("/")
                ctype = child.get("ContentType", "")
                self.content_types[part_name] = ctype
                if part_name in self.entries:
                    self.entries[part_name].content_type = ctype

    def _get_rels_path_for_part(self, part_path: str) -> str:
        p = Path(part_path)
        parent = p.parent.as_posix()
        if parent == ".":
            return f"_rels/{p.name}.rels"
        return f"{parent}/_rels/{p.name}.rels"

    def _parse_relationships(self, rels_part_path: str, owner_part: str) -> None:
        raw = self.raw_parts[rels_part_path]
        if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
            raise SecurityViolationError(f"Relationship part '{rels_part_path}' contains forbidden DTD/Entity declaration.")
        try:
            tree = etree.fromstring(raw, HARDENED_XML_PARSER)
        except etree.XMLSyntaxError as e:
            raise SecurityViolationError(f"Malformed relationship part '{rels_part_path}': {e}")

        rels: List[OpcRelationship] = []
        for child in tree:
            if etree.QName(child).localname == "Relationship":
                rel_id = child.get("Id", "")
                rel_type = child.get("Type", "")
                target = child.get("Target", "")
                target_mode = child.get("TargetMode", "Internal")
                
                # If internal and relative, resolve against owner part directory
                if target_mode != "External" and not target.startswith("/"):
                    if owner_part != "/":
                        parent_dir = Path(owner_part).parent.as_posix()
                        if parent_dir != ".":
                            resolved = Path(f"{parent_dir}/{target}").resolve().as_posix()
                            # Strip leading slash on Windows or POSIX resolve artifacts if any
                            if resolved.startswith("/"):
                                target = resolved.lstrip("/")
                            else:
                                # Simple POSIX relative join
                                parts = f"{parent_dir}/{target}".split("/")
                                resolved_parts = []
                                for pt in parts:
                                    if pt == "..":
                                        if resolved_parts:
                                            resolved_parts.pop()
                                    elif pt and pt != ".":
                                        resolved_parts.append(pt)
                                target = "/".join(resolved_parts)
                    else:
                        target = target.lstrip("/")
                elif target.startswith("/"):
                    target = target.lstrip("/")

                rels.append(OpcRelationship(
                    rel_id=rel_id,
                    rel_type=rel_type,
                    target=target,
                    target_mode=target_mode
                ))
                
        self.relationships[owner_part] = rels

    def get_part_content(self, part_path: str) -> bytes:
        """Safely retrieves raw bytes of an internal package part."""
        norm = part_path.lstrip("/")
        if norm not in self.raw_parts:
            raise KeyError(f"Part '{norm}' not found in package.")
        return self.raw_parts[norm]

    def get_xml_tree(self, part_path: str) -> etree._Element:
        """Safely parses and returns lxml ElementTree root for an XML part."""
        raw = self.get_part_content(part_path)
        if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
            raise SecurityViolationError(f"XML part '{part_path}' contains forbidden DTD/Entity declaration.")
        try:
            return etree.fromstring(raw, HARDENED_XML_PARSER)
        except etree.XMLSyntaxError as e:
            raise SecurityViolationError(f"Malformed XML in part '{part_path}': {e}")
