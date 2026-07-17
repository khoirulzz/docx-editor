import io
import zipfile
from lxml import etree
from app.docx.package import OpcPackage
from app.docx.serializer import DocxSerializer

def test_docx_serializer_preserves_untouched_entries():
    # Create a mock docx with document.xml and an extra binary asset
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        zf.writestr("_rels/.rels", b'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        zf.writestr("word/document.xml", b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Old</w:t></w:r></w:p></w:body></w:document>')
        zf.writestr("word/media/image1.png", b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01')
        zf.writestr("word/styles.xml", b'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')

    pkg = OpcPackage(buf.getvalue())
    serializer = DocxSerializer(pkg)

    # Mutate document.xml using lxml Element tree
    root = pkg.get_xml_tree("word/document.xml")
    t_elem = root.find(".//w:t", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
    t_elem.text = "New Content"

    proposal_bytes, sha256_hash = serializer.serialize({"word/document.xml": root})

    # Verify sha256 prefix
    assert sha256_hash.startswith("sha256:")

    # Read back proposed docx
    out_pkg = OpcPackage(proposal_bytes)
    assert "word/media/image1.png" in out_pkg.entries.keys()
    assert out_pkg.get_part_content("word/media/image1.png") == b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    assert out_pkg.get_part_content("word/styles.xml") == b'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'

    # Verify mutated xml content
    new_xml = out_pkg.get_part_content("word/document.xml")
    assert b"New Content" in new_xml
    assert b"Old" not in new_xml
