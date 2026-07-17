# ADR-005: Protected Subtree Fingerprints

Status: Accepted.

Decision: Normative preservation uses exact instruction string plus canonical XML/result/boundary hashes. Whole `document.xml` byte identity is not guaranteed after parse/serialize.

Rationale: semantically identical XML may serialize differently. Untouched non-mutated ZIP parts remain byte-identical where possible.
