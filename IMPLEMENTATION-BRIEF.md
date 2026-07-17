# Implementation Brief for an AI Coding Agent

Build the application described in this workspace as a production-oriented, test-first FastAPI web app. Begin with Milestone 0 and continue sequentially. Do not implement native Mendeley insertion before the safe package inspector, versioned executor, reference intake, CSL mode, and full verification pipeline exist.

## Mandatory first response from the coding agent

Before coding, produce:

1. requirement-to-module map;
2. requirement-to-test map;
3. proposed repository tree;
4. milestone 0–2 implementation sequence;
5. unresolved environment dependencies, especially Microsoft Word/Mendeley fixture access.

Do not reopen architectural decisions already marked Accepted unless implementation evidence proves them impossible. New decisions require an ADR.

## Mandatory runtime behavior

- User uploads DOCX and optional loose reference files.
- System safely inspects the package and references.
- User chats naturally; system chooses a bounded scope.
- Planner returns schema-valid operations only.
- Deterministic executor creates an isolated proposal.
- Verification blocks unsafe output.
- User reviews operation-level diff and citation status.
- Commit creates immutable version; export produces DOCX and optional citation bundle.

## Mandatory honesty

The UI and documentation must distinguish:

- existing Mendeley fields preserved;
- new APA citations formatted but not managed;
- placeholders requiring Mendeley insertion;
- native managed citations verified by a qualified adapter.

Never collapse these statuses into a single “Mendeley ready” label.
