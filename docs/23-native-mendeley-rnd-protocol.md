# Native Mendeley Adapter R&D Protocol

## 1. Purpose

Derive a tested compatibility adapter without pretending that undocumented structures form a stable public contract.

## 2. Fixture acquisition

For each environment record:

- operating system;
- Microsoft Word build;
- Mendeley Reference Manager version;
- Mendeley Cite/add-in version;
- citation style;
- locale;
- source reference metadata.

Create documents using official add-in actions only:

1. empty document;
2. one citation;
3. multi-item citation;
4. narrative-like variants where possible;
5. page locator/prefix/suffix;
6. bibliography;
7. edit metadata then refresh;
8. same-author/year disambiguation.

Store original and post-action hashes. Fixtures must not contain copyrighted full text beyond minimal test sentences.

## 3. Package diffing

Compare ZIP entries before/after official insertion:

- added/removed/changed parts;
- relationships and content types;
- custom XML/web extension/taskpane parts;
- field/content-control structures;
- settings changes;
- bibliography coupling.

Use semantic XML diff plus raw-byte inspection. Do not infer a writer from one sample.

## 4. Adapter design rules

- Legacy and modern implementations are separate adapters.
- Preserve unknown keys/elements.
- Generate IDs according to observed constraints, with collision checks.
- Render display text with same style processor/input data or mark field dirty if verified behavior requires it.
- Never copy user/library secrets or account-specific identifiers across users.
- Do not mutate custom parts unless fixture evidence and tests require it.

## 5. Qualification record

```yaml
adapter: legacy-mendeley-field
adapter_version: 0.3.0
producer: Mendeley Desktop Word Plugin
word_versions: [...]
plugin_versions: [...]
fixtures: [...]
openxml_validation: pass
select_edit_refresh: pass
style_change: pass
bibliography: pass
save_reopen: pass
known_limitations: [...]
qualified_at: ...
```

## 6. Failure policy

If Word displays a repair dialog, Mendeley cannot select/edit the citation, style refresh breaks, or an untouched field changes unexpectedly, qualification fails. Feature flag remains off.

## 7. Legal/ethical boundary

Use documents created by the development team with software they are authorized to use. Do not distribute proprietary plugin code or confidential user files. Record observed document interoperability facts and original implementation code only.
