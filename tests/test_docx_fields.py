import pytest
from lxml import etree
from app.docx.fields import FieldStateMachine, FieldInstance, W_NS

def create_mock_field_xml(instruction_text: str, result_text: str = "Result") -> bytes:
    return f'''<w:p xmlns:w="{W_NS}">
        <w:r><w:fldChar w:fldCharType="begin"/></w:r>
        <w:r><w:instrText xml:space="preserve">{instruction_text}</w:instrText></w:r>
        <w:r><w:fldChar w:fldCharType="separate"/></w:r>
        <w:r><w:t>{result_text}</w:t></w:r>
        <w:r><w:fldChar w:fldCharType="end"/></w:r>
    </w:p>'''.encode("utf-8")

def test_field_state_machine_mendeley_citation():
    xml = create_mock_field_xml(" ADDIN Mendeley Citation CSL_CITATION {} ", "(Smith, 2020)")
    root = etree.fromstring(xml)
    
    fsm = FieldStateMachine()
    fields = fsm.process_element_tree(root)
    
    assert len(fields) == 1
    f = fields[0]
    assert f.field_type == "mendeley_legacy_citation"
    assert f.is_protected is True
    assert "ADDIN Mendeley Citation" in f.instruction
    assert f.fingerprint_sha256.startswith("sha256:")

def test_field_state_machine_toc_and_page():
    xml = f'''<w:body xmlns:w="{W_NS}">
        <w:p>
            <w:r><w:fldChar w:fldCharType="begin"/></w:r>
            <w:r><w:instrText>TOC \\o "1-3"</w:instrText></w:r>
            <w:r><w:fldChar w:fldCharType="separate"/></w:r>
            <w:r><w:t>Table of Contents</w:t></w:r>
            <w:r><w:fldChar w:fldCharType="end"/></w:r>
        </w:p>
        <w:p>
            <w:r><w:fldChar w:fldCharType="begin"/></w:r>
            <w:r><w:instrText>PAGE</w:instrText></w:r>
            <w:r><w:fldChar w:fldCharType="separate"/></w:r>
            <w:r><w:t>1</w:t></w:r>
            <w:r><w:fldChar w:fldCharType="end"/></w:r>
        </w:p>
    </w:body>'''.encode("utf-8")
    root = etree.fromstring(xml)
    
    fsm = FieldStateMachine()
    fields = fsm.process_element_tree(root)
    
    assert len(fields) == 2
    assert fields[0].field_type == "table_of_contents"
    assert fields[0].is_protected is True
    
    assert fields[1].field_type == "page_number"
    assert fields[1].is_protected is False

def test_nested_complex_fields():
    # Test a complex field nested inside another (e.g. IF or hyperlink inside TOC or citation)
    xml = f'''<w:p xmlns:w="{W_NS}">
        <w:r><w:fldChar w:fldCharType="begin"/></w:r>
        <w:r><w:instrText>OuterField </w:instrText></w:r>
            <w:r><w:fldChar w:fldCharType="begin"/></w:r>
            <w:r><w:instrText>InnerPAGE</w:instrText></w:r>
            <w:r><w:fldChar w:fldCharType="separate"/></w:r>
            <w:r><w:t>1</w:t></w:r>
            <w:r><w:fldChar w:fldCharType="end"/></w:r>
        <w:r><w:fldChar w:fldCharType="separate"/></w:r>
        <w:r><w:t>OuterResult</w:t></w:r>
        <w:r><w:fldChar w:fldCharType="end"/></w:r>
    </w:p>'''.encode("utf-8")
    root = etree.fromstring(xml)
    
    fsm = FieldStateMachine()
    fields = fsm.process_element_tree(root)
    
    assert len(fields) == 2
    # Inner field completes first
    assert fields[0].instruction == "InnerPAGE"
    # Outer field completes second
    assert fields[1].instruction == "OuterField InnerPAGE"

def test_fingerprint_sha256_detects_mutation():
    xml1 = create_mock_field_xml("ADDIN Mendeley Citation CSL_CITATION {}", "(Smith, 2020)")
    xml2 = create_mock_field_xml("ADDIN Mendeley Citation CSL_CITATION {}", "(Smith, 2021)") # Result tampered
    
    f1 = FieldStateMachine().process_element_tree(etree.fromstring(xml1))[0]
    f2 = FieldStateMachine().process_element_tree(etree.fromstring(xml2))[0]
    
    assert f1.fingerprint_sha256 != f2.fingerprint_sha256
