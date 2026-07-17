# Algorithms and Pseudocode

This document clarifies expected algorithms. Implementations may differ internally while preserving behavior, complexity bounds, and tests.

## 1. Safe archive inspection

```python
def inspect_archive(file, limits):
    assert file.size <= limits.max_compressed
    with ZipFile(file) as z:
        infos = z.infolist()
        assert len(infos) <= limits.max_entries
        seen = set()
        total = 0
        for info in infos:
            name = normalize_zip_path(info.filename)
            assert is_relative_safe_path(name)
            assert name not in seen
            assert not is_encrypted(info)
            seen.add(name)
            total += info.file_size
            assert info.file_size <= limits.max_entry
            assert total <= limits.max_uncompressed
            assert safe_ratio(info.file_size, info.compress_size) <= limits.max_ratio
        return build_inventory_without_extracting_arbitrary_paths(z)
```

Prefer reading entries directly from ZIP into bounded buffers/streams. If extracting, create a private session directory and enforce path containment after resolution.

## 2. OPC main-part discovery

```python
root_rels = parse('_rels/.rels')
office_rel = exactly_one(root_rels, type=OFFICE_DOCUMENT_REL)
main_part = resolve_internal_target('/', office_rel.target)
assert content_type(main_part) in ALLOWED_WORD_MAIN_TYPES
```

Do not assume `word/document.xml` without validating relationships.

## 3. Complex-field parser

```python
def parse_story(events):
    stack = []
    fields = []
    for event in events_in_document_order():
        if event.is_fldchar('begin'):
            stack.append(FieldFrame(begin=event.locator, depth=len(stack)))
        elif event.is_instr_text() and stack:
            stack[-1].instruction_fragments.append(event.exact_text)
            stack[-1].instruction_nodes.append(event.locator)
        elif event.is_fldchar('separate') and stack:
            assert stack[-1].separate is None or mark_malformed(stack[-1])
            stack[-1].separate = event.locator
            stack[-1].phase = 'result'
        elif event.is_fldchar('end'):
            if not stack:
                record_orphan_end(event)
            else:
                frame = stack.pop()
                frame.end = event.locator
                fields.append(finalize(frame))
        elif stack and stack[-1].phase == 'result':
            stack[-1].result_events.append(event)
    for frame in stack:
        mark_unclosed_and_protect(frame)
    return fields
```

Nested fields are associated with their own frames. Parent frames record child field references rather than flattening them blindly.

## 4. Paragraph stable identity

```python
def identify_paragraph(p, context):
    if unique_nonempty(p.w14_para_id, context.story):
        natural_key = f'{context.story}:{p.w14_para_id}'
    else:
        natural_key = sha256_json({
            'story': context.story,
            'parent_chain': parent_semantic_chain(p),
            'style': p.style_id,
            'text': normalize_for_identity(project_visible_text(p)),
            'prev': neighbor_hash(p, -1),
            'next': neighbor_hash(p, +1),
        })
    return session_node_id(natural_key)
```

Fallback identity is not used to silently relocate writes after a version mismatch. It helps diagnostics/re-inspection; write still requires version and exact preconditions.

## 5. Span edit planning validation

```python
def validate_span(op, node):
    assert op.target.expected_text_hash == node.text_hash
    assert 0 <= op.start_offset <= op.end_offset <= len(node.visible_text)
    assert node.visible_text[op.start_offset:op.end_offset] == op.expected_text
    assert not overlaps(op.range, node.protected_intervals)
    assert node.editability.replace_text_span
```

## 6. Run splitting

```python
def replace_span(paragraph, projection, start, end, replacement, policy):
    start_point = projection.locate(start)
    end_point = projection.locate(end)
    split_text_node_at(start_point)
    split_text_node_at(end_point)
    remove_only_text_fragments_fully_inside(start, end)
    insert_text_run(replacement, properties=resolve_format_policy(policy, start_point, end_point))
    normalize_xml_space_on_affected_text_nodes()
```

Never delete protected siblings while replacing text.

## 7. Protected citation fingerprint

```python
def fingerprint(field):
    return {
        'instruction_sha256': sha256(field.exact_instruction_utf8),
        'canonical_subtree_sha256': sha256(canonicalize(field.covered_xml)),
        'result_text_sha256': sha256(field.visible_result_text_utf8),
        'boundary_signature': [field.story_id, field.depth, field.has_separator,
                               relative_anchor(field.begin), relative_anchor(field.end)],
    }
```

For untouched fields compare every component. Count equality alone is insufficient.

## 8. Reference intake

```python
def intake(assets):
    candidates = []
    for asset in assets:
        parsed = parser_for(asset).parse_bounded(asset)
        candidates += segment_sources_and_evidence(parsed)
    normalized = normalize_without_guessing(candidates)
    resolved = resolve_identifiers_then_titles(normalized)
    groups = deduplicate_with_confidence(resolved)
    return build_reference_pack(groups)
```

## 9. Evidence retrieval

```python
def retrieve(query, section, store, k=12):
    pool = lexical_search(store, combine(query, section.heading, section.nearby_text), top_n=50)
    pool = filter_citation_ready_or_reviewable(pool)
    ranked = rerank(pool, relevance_and_evidence_quality)
    return diversify(ranked, by=['reference_id', 'evidence_role', 'publication_year'])[:k]
```

## 10. Plan Gateway

```python
def accept_plan(raw, session):
    obj = strict_json_parse(raw)
    validate_json_schema(obj)
    assert obj.document_version == session.current_version
    validate_scope(obj.scope, session.graph)
    validate_operation_dependencies(obj.operations)
    validate_each_operation(obj, session.graph)
    validate_reference_evidence_links(obj, session.reference_store)
    enforce_limits_and_user_policy(obj)
    return ValidatedPlan(obj)
```

## 11. Proposal and commit

```python
def create_proposal(plan, base):
    workspace = isolated_copy(base.package)
    result = executor.apply(plan, workspace)
    verification = verifier.run(base, result)
    if not verification.blocking_pass:
        return FailedProposal(result, verification)
    return ReviewableProposal(result, verification)

def commit(proposal, expected_head):
    with session_lock(proposal.session_id):
        assert current_head() == expected_head == proposal.base_version
        assert proposal.verification.blocking_pass
        return atomic_publish_as_next_version(proposal.package)
```
