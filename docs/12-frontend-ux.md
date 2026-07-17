# Frontend UX Specification

## 1. Main screens

### Workspace upload

- primary DOCX picker;
- optional supporting files;
- privacy notice;
- clear supported formats and limits;
- progress and inspection errors.

### Document workspace

- document outline left panel;
- chat/instruction panel;
- document text preview;
- source/reference status;
- version indicator.

### Proposal review

- operation list grouped by section/dependency;
- before/after diff;
- citation chips linked to source/evidence detail;
- formatting/structural impact;
- verification badges;
- accept/reject all and per group.

## 2. Simplified reference UX

After intake show:

```text
18 sources detected
12 ready
4 need review
2 unresolved
```

Do not require schema fields. For ambiguous items show candidate selection with title/author/year/DOI and match reason.

## 3. Citation labels

Every new citation displays one of:

- Managed Mendeley
- APA formatted, not managed
- Requires final insertion in Mendeley

Never hide this distinction.

## 4. Chat instruction behavior

The system may infer defaults from document and prior session preferences, but always surface them in proposal:

- target scope;
- style (e.g. APA 7);
- direct quote/paraphrase policy;
- source policy;
- citation insertion mode.

## 5. Warning hierarchy

- blocking: proposal cannot commit;
- decision required: user must choose;
- advisory: can commit;
- informational.

## 6. Accessibility

Keyboard navigation, visible focus, semantic controls, proper labels, diff alternatives for screen readers, no color-only statuses, and downloadable plain-text report.

## 7. Error recovery

Keep user inputs and uploads associated with session after recoverable errors. Offer retry for provider call without reparsing. Never suggest re-upload unless source is unavailable/corrupt.
