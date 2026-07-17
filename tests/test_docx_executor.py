import pytest
from lxml import etree
from app.docx.package import OpcPackage
from app.docx.inspector import DocxInspector
from app.docx.anchors import AnchorResolver
from app.docx.executor import DocxMutationExecutor
from app.models.domain import (
    ReplaceTextSpanOperation,
    InsertParagraphOperation,
    TextContentBlock,
    CitationContentBlock,
    TargetLocator,
    InsertParagraphPolicy,
)
from app.core.errors import PreconditionFailedError
from tests.test_package_security import create_mock_docx

def test_anchor_resolver_and_precondition_check():
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">
        <w:body>
            <w:p w14:paraId="ABC12345">
                <w:r><w:t>Hello world</w:t></w:r>
            </w:p>
        </w:body>
    </w:document>'''
    pkg = OpcPackage(create_mock_docx({"word/document.xml": mock_xml}))
    inspector = DocxInspector(pkg)
    graph = inspector.build_graph()
    root = pkg.get_xml_tree("word/document.xml")
    
    resolver = AnchorResolver(root, graph)
    
    # Correct hash matches
    elem, node = resolver.resolve(TargetLocator(node_id="para_0", expected_text_hash=graph.nodes[0].text_hash))
    assert node.para_id == "ABC12345"
    
    # Mismatched hash raises PreconditionFailedError
    with pytest.raises(PreconditionFailedError) as exc:
        resolver.resolve(TargetLocator(node_id="para_0", expected_text_hash="sha256:stale_hash"))
    assert "text hash mismatch after planning" in str(exc.value)

def test_execute_replace_span_multi_run():
    # Paragraph where "brown fox" spans across two runs: run 1 has "brown ", run 2 has "fox jumps"
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">
        <w:body>
            <w:p w14:paraId="RUNTEST1">
                <w:r><w:rPr><w:b/></w:rPr><w:t>The brown </w:t></w:r>
                <w:r><w:t>fox jumps over the dog.</w:t></w:r>
            </w:p>
        </w:body>
    </w:document>'''
    pkg = OpcPackage(create_mock_docx({"word/document.xml": mock_xml}))
    inspector = DocxInspector(pkg)
    graph = inspector.build_graph()
    root = pkg.get_xml_tree("word/document.xml")
    
    executor = DocxMutationExecutor(root, graph)
    op = ReplaceTextSpanOperation(
        operation_id="op_1",
        target=TargetLocator(node_id="para_0", expected_text_hash=graph.nodes[0].text_hash),
        expected_text="brown fox",
        replacement_content=[TextContentBlock(text="red cat")]
    )
    
    diffs = executor.execute_operations([op])
    assert len(diffs) == 1
    assert diffs[0].after_text == "The red cat jumps over the dog."
    
    # Verify XML runs structure in root
    from app.docx.fields import W_NS
    new_text = "".join(t.text for t in root.findall(f".//{{{W_NS}}}t"))
    assert new_text == "The red cat jumps over the dog."

def test_execute_insert_paragraph_and_citation():
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">
        <w:body>
            <w:p w14:paraId="P1"><w:r><w:t>Paragraf pertama.</w:t></w:r></w:p>
        </w:body>
    </w:document>'''
    pkg = OpcPackage(create_mock_docx({"word/document.xml": mock_xml}))
    graph = DocxInspector(pkg).build_graph()
    root = pkg.get_xml_tree("word/document.xml")
    
    # Provide mock reference store for citation rendering
    ref_store = {
        "ref_smith2024": {
            "title": "AI in DOCX",
            "author": [{"family": "Smith", "given": "John"}],
            "issued": {"date-parts": [[2024]]}
        }
    }
    executor = DocxMutationExecutor(root, graph, reference_store=ref_store)
    
    op = InsertParagraphOperation(
        operation_id="op_2",
        type="insert_paragraph_after",
        target=TargetLocator(node_id="para_0", expected_text_hash=graph.nodes[0].text_hash),
        content=[
            TextContentBlock(text="Menurut riset terbaru "),
            CitationContentBlock(
                reference_ids=["ref_smith2024"],
                evidence_ids=["ev_1"],
                citation_mode="parenthetical"
            )
        ],
        paragraph_style_policy=InsertParagraphPolicy(inherit_paragraph_style=True)
    )
    
    diffs = executor.execute_operations([op])
    assert diffs[0].after_text == "Menurut riset terbaru (Smith, 2024)"

def test_protected_paragraph_rejection():
    mock_xml = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p>
                <w:r><w:fldChar w:fldCharType="begin"/></w:r>
                <w:r><w:instrText>ADDIN Mendeley Citation CSL_CITATION {}</w:instrText></w:r>
                <w:r><w:fldChar w:fldCharType="separate"/></w:r>
                <w:r><w:t>(Smith, 2020)</w:t></w:r>
                <w:r><w:fldChar w:fldCharType="end"/></w:r>
            </w:p>
        </w:body>
    </w:document>'''
    pkg = OpcPackage(create_mock_docx({"word/document.xml": mock_xml}))
    graph = DocxInspector(pkg).build_graph()
    root = pkg.get_xml_tree("word/document.xml")
    
    executor = DocxMutationExecutor(root, graph)
    op = ReplaceTextSpanOperation(
        operation_id="op_prot",
        target=TargetLocator(node_id="para_0", expected_text_hash=graph.nodes[0].text_hash),
        expected_text="(Smith, 2020)",
        replacement_content=[TextContentBlock(text="(Smith, 2021)")]
    )
    
    with pytest.raises(PreconditionFailedError) as exc:
        executor.execute_operations([op])
    assert "Target node 'para_0' is protected" in str(exc.value)
