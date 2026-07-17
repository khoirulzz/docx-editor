import io
import zipfile
import pytest
from app.docx.package import OpcPackage
from app.core.errors import ArchiveLimitExceededError, PreconditionFailedError, SecurityViolationError

def create_mock_docx(
    entries: dict[str, bytes],
    add_content_types: bool = True,
    add_rels: bool = True,
    main_doc_path: str = "word/document.xml"
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if add_content_types and "[Content_Types].xml" not in entries:
            zf.writestr(
                "[Content_Types].xml",
                f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                f'<Override PartName="/{main_doc_path}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                f'</Types>'
            )
        if add_rels and "_rels/.rels" not in entries:
            zf.writestr(
                "_rels/.rels",
                f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="{main_doc_path}"/>'
                f'</Relationships>'
            )
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()

def test_valid_opc_package_and_relationship_discovery():
    mock_doc_xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'
    docx_bytes = create_mock_docx({"word/document.xml": mock_doc_xml})
    
    pkg = OpcPackage(docx_bytes)
    assert pkg.main_document_part == "word/document.xml"
    assert "word/document.xml" in pkg.entries
    assert pkg.get_part_content("word/document.xml") == mock_doc_xml

def test_missing_content_types():
    docx_bytes = create_mock_docx({"word/document.xml": b"<doc/>"}, add_content_types=False)
    with pytest.raises(SecurityViolationError) as exc:
        OpcPackage(docx_bytes)
    assert "Missing required part: [Content_Types].xml" in str(exc.value)

def test_missing_rels():
    docx_bytes = create_mock_docx({"word/document.xml": b"<doc/>"}, add_rels=False)
    with pytest.raises(SecurityViolationError) as exc:
        OpcPackage(docx_bytes)
    assert "Missing required relationship part: _rels/.rels" in str(exc.value)

def test_path_traversal_rejection():
    # Attempt .. traversal
    docx_bytes = create_mock_docx({"word/../../etc/passwd": b"root:x:0:0"})
    with pytest.raises(SecurityViolationError) as exc:
        OpcPackage(docx_bytes)
    assert "Path traversal ('..') in ZIP entry path rejected" in str(exc.value)

def test_absolute_path_rejection():
    docx_bytes = create_mock_docx({"/etc/passwd": b"root:x:0:0"})
    with pytest.raises(SecurityViolationError) as exc:
        OpcPackage(docx_bytes)
    assert "Absolute ZIP entry path rejected" in str(exc.value)

def test_nul_byte_rejection():
    from app.core.security import normalize_and_validate_zip_entry_path
    with pytest.raises(SecurityViolationError) as exc:
        normalize_and_validate_zip_entry_path("word/doc\x00.xml")
    assert "ZIP entry path contains NUL byte" in str(exc.value)

    # Also test via package where rels point to NUL path or entry has NUL if zipfile preserves it
    docx_bytes = create_mock_docx({"word/doc\x00.xml": b"<doc/>"}, main_doc_path="word/doc\x00.xml")
    with pytest.raises((SecurityViolationError, PreconditionFailedError)):
        OpcPackage(docx_bytes)

def test_max_entries_exceeded(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_ZIP_ENTRIES", 5)
    entries = {f"word/file_{i}.xml": b"<data/>" for i in range(10)}
    docx_bytes = create_mock_docx(entries)
    with pytest.raises(ArchiveLimitExceededError) as exc:
        OpcPackage(docx_bytes)
    assert "exceeding limit of 5" in str(exc.value)

def test_compression_ratio_zip_bomb_protection(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_COMPRESSION_RATIO", 10)
    
    # Create high ratio zip entry
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
        )
        zf.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        )
        # Highly compressible repeating bytes (e.g. 1 MB of zeros compresses to ~1 KB, ratio ~1000)
        zf.writestr("word/document.xml", b"0" * 100_000)
    
    docx_bytes = buf.getvalue()
    with pytest.raises(ArchiveLimitExceededError) as exc:
        OpcPackage(docx_bytes)
    assert "exceeds safety threshold of 10" in str(exc.value)

def test_xxe_protection():
    # Test that HARDENED_XML_PARSER rejects/ignores entity declarations or does not resolve external entities
    xxe_xml = b'''<?xml version="1.0"?>
    <!DOCTYPE foo [
      <!ELEMENT foo ANY >
      <!ENTITY xxe SYSTEM "file:///etc/passwd" >]><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>&xxe;</w:body></w:document>'''
    
    docx_bytes = create_mock_docx({"word/document.xml": xxe_xml})
    pkg = OpcPackage(docx_bytes)
    # Since resolve_entities=False and no_network=True, get_xml_tree will either error or not resolve &xxe;
    with pytest.raises(SecurityViolationError):
        pkg.get_xml_tree("word/document.xml")
