# Skill: Verification

Use when implementing package/XML/OpenXML/citation/semantic verification.

## Procedure

1. Compare base and proposal manifests.
2. Run hardened reparse and OpenXmlValidator.
3. Evaluate protected subtree fingerprints.
4. Check changed-part allowlist and operation outcomes.
5. Native citation adapter needs Word/Mendeley round-trip evidence.
6. A failure blocks commit and preserves base.

## Safety boundary

This skill never authorizes an AI model to directly mutate XML. Follow `AGENTS.md`, schemas, and non-negotiable requirements. Fail closed and preserve original files.

