import pytest
from app.models.domain import DocumentGraph, VerificationStatus
from app.verification.openxml import OpenXmlValidator
from app.verification.citations import CitationIntegrityVerifier
from app.verification.pipeline import VerificationPipeline
from tests.test_package_security import create_mock_docx

def test_openxml_validator():
    validator = OpenXmlValidator()
    mock_xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'
    res = validator.validate_xml_part("word/document.xml", mock_xml)
    assert res.status == VerificationStatus.PASS
    assert res.checks[0]["check"] == "well_formed_syntax"

def test_citation_integrity_verifier():
    f_base = {"field_id": "fld_0", "field_type": "mendeley_legacy_citation", "is_protected": True, "fingerprint_sha256": "hash_1"}
    base_graph = DocumentGraph(document_id="d1", version=1, package_sha256="abc", fields=[f_base])
    
    # 1. Intact proposal graph
    prop_graph_ok = DocumentGraph(document_id="d1", version=2, package_sha256="xyz", fields=[f_base])
    res_ok = CitationIntegrityVerifier.verify(base_graph, prop_graph_ok)
    assert res_ok.status == VerificationStatus.PASS

    # 2. Tampered fingerprint
    f_tampered = {"field_id": "fld_0", "field_type": "mendeley_legacy_citation", "is_protected": True, "fingerprint_sha256": "hash_2"}
    prop_graph_bad = DocumentGraph(document_id="d1", version=2, package_sha256="xyz", fields=[f_tampered])
    res_bad = CitationIntegrityVerifier.verify(base_graph, prop_graph_bad)
    assert res_bad.status == VerificationStatus.FAIL
    assert "fingerprint altered" in res_bad.checks[0]["detail"]

def test_verification_pipeline_blocking_pass():
    mock_xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'
    docx_bytes = create_mock_docx({"word/document.xml": mock_xml})
    
    base_graph = DocumentGraph(document_id="d1", version=1, package_sha256="abc")
    prop_graph = DocumentGraph(document_id="d1", version=2, package_sha256="xyz")
    
    pipeline = VerificationPipeline()
    report = pipeline.run_pipeline(docx_bytes, base_graph, prop_graph)
    
    assert report.blocking_pass is True
    assert report.levels.package.status == VerificationStatus.PASS
    assert report.levels.xml.status == VerificationStatus.PASS
    assert report.levels.structural.status == VerificationStatus.PASS
    assert report.levels.citations.status == VerificationStatus.PASS
    assert report.levels.semantic.status == VerificationStatus.PASS

def test_verification_pipeline_blocks_on_l5_failure():
    mock_xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'
    docx_bytes = create_mock_docx({"word/document.xml": mock_xml})
    
    f_base = {"field_id": "fld_0", "field_type": "table_of_contents", "is_protected": True, "fingerprint_sha256": "toc_hash_1"}
    base_graph = DocumentGraph(document_id="d1", version=1, package_sha256="abc", fields=[f_base])
    
    # Proposal graph missing TOC field
    prop_graph = DocumentGraph(document_id="d1", version=2, package_sha256="xyz", fields=[])
    
    pipeline = VerificationPipeline()
    report = pipeline.run_pipeline(docx_bytes, base_graph, prop_graph)
    
    assert report.blocking_pass is False
    assert report.levels.citations.status == VerificationStatus.FAIL
    assert any(err["level"] == "L5" for err in report.errors)
