import pytest
from lxml import etree
from app.docx.package import OpcPackage
from app.docx.inspector import DocxInspector, IndonesianChapterDetector
from tests.test_package_security import create_mock_docx

def test_indonesian_chapter_detector():
    # Test level 1 detection
    lvl, cid, title = IndonesianChapterDetector.detect_level("BAB I PENDAHULUAN")
    assert lvl == 1
    assert cid is not None
    assert title == "BAB I PENDAHULUAN"

    lvl2, cid2, title2 = IndonesianChapterDetector.detect_level("BAB II : TINJAUAN PUSTAKA")
    assert lvl2 == 1
    assert "TINJAUAN PUSTAKA" in title2

    # Test level 2 detection
    lvl_sub, cid_sub, title_sub = IndonesianChapterDetector.detect_level("1.1 Latar Belakang")
    assert lvl_sub == 2
    assert title_sub == "1.1 Latar Belakang"

    # Test style override
    lvl_style, cid_style, title_style = IndonesianChapterDetector.detect_level("Abstrak", style_id="Heading1")
    assert lvl_style == 1

def test_docx_inspector_builds_graph_and_chapters():
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">
        <w:body>
            <w:p w14:paraId="11111111">
                <w:r><w:t>BAB I PENDAHULUAN</w:t></w:r>
            </w:p>
            <w:p w14:paraId="22222222">
                <w:r><w:t>1.1 Latar Belakang</w:t></w:r>
            </w:p>
            <w:p w14:paraId="33333333">
                <w:r><w:t>Paragraf isi tentang penelitian.</w:t></w:r>
            </w:p>
            <w:tbl>
                <w:tr><w:tc><w:p><w:r><w:t>Data 1</w:t></w:r></w:p></w:tc></w:tr>
            </w:tbl>
        </w:body>
    </w:document>'''
    
    docx_bytes = create_mock_docx({"word/document.xml": mock_xml})
    pkg = OpcPackage(docx_bytes)
    
    inspector = DocxInspector(pkg)
    graph = inspector.build_graph()
    
    assert graph.schema_version == "document-graph/1.0"
    assert len(graph.nodes) == 4  # 3 paragraphs + 1 table
    assert graph.nodes[0].node_id == "para_0"
    assert graph.nodes[0].para_id == "11111111"
    assert graph.nodes[0].outline_level == 1
    assert graph.nodes[0].text == "BAB I PENDAHULUAN"
    
    assert graph.nodes[1].node_id == "para_1"
    assert graph.nodes[1].outline_level == 2
    assert graph.nodes[1].parent_node_id == graph.nodes[0].features["chapter_id"]
    
    assert graph.nodes[2].node_id == "para_2"
    assert graph.nodes[2].parent_node_id == graph.nodes[0].features["chapter_id"]
    
    assert graph.nodes[3].node_id == "tbl_3"
    assert graph.nodes[3].node_type == "table"
    
    assert len(graph.chapters) == 1
    assert graph.chapters[0]["title"] == "BAB I PENDAHULUAN"

def test_inspector_marks_protected_fields_uneditable():
    # Paragraph with Mendeley citation inside
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p>
                <w:r><w:t>Menurut penelitian </w:t></w:r>
                <w:r><w:fldChar w:fldCharType="begin"/></w:r>
                <w:r><w:instrText>ADDIN Mendeley Citation CSL_CITATION {}</w:instrText></w:r>
                <w:r><w:fldChar w:fldCharType="separate"/></w:r>
                <w:r><w:t>(Smith, 2020)</w:t></w:r>
                <w:r><w:fldChar w:fldCharType="end"/></w:r>
            </w:p>
            <w:p>
                <w:r><w:t>Paragraf biasa yang aman diedit.</w:t></w:r>
            </w:p>
        </w:body>
    </w:document>'''
    
    docx_bytes = create_mock_docx({"word/document.xml": mock_xml})
    pkg = OpcPackage(docx_bytes)
    inspector = DocxInspector(pkg)
    graph = inspector.build_graph()
    
    assert len(graph.nodes) == 2
    assert graph.nodes[0].editability["editable"] is False
    assert "mendeley_legacy_citation" in graph.nodes[0].editability["reason"]
    
    assert graph.nodes[1].editability["editable"] is True
