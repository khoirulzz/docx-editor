# Implementation Plan

## Milestone 0 — Repository and contracts

- Set up FastAPI, frontend shell, tests, lint/type checks.
- Load JSON Schemas and OpenAPI.
- Config/secret validation.
- CI including schema validation.

Exit: health endpoint, package builds, contracts validate.

## Milestone 1 — Safe package inspection

- Upload gateway and archive limits.
- OPC relationship discovery.
- hardened XML parser.
- DocumentGraph, text projection, style/outline detection.
- field state machine and protected classifier.

Exit: fixture inspection reports correct paragraphs, fields, chapters; no mutations.

## Milestone 2 — Versioned safe editing vertical slice

- session/version store;
- manual typed edit plan endpoint for tests;
- span replace and safe paragraph insert;
- proposal isolation;
- diff and commit/export;
- basic package/XML verification.

Exit: safe plain-document round trips and undo/versioning.

## Milestone 3 — Agent planning

- Blackbox client/provider registry;
- scope selector and planner prompts;
- strict schema + semantic Plan Gateway;
- token budgeting/retries;
- chat proposal API/UI.

Exit: user instruction generates bounded verified proposal.

## Milestone 4 — Reference intake

- loose TXT/MD parser;
- BibTeX/RIS/CSL-JSON parsers;
- reference/evidence schemas;
- Crossref DOI/title resolver;
- dedupe/confidence/review UI;
- retrieval and evidence-linked planning.

Exit: messy notes become reviewable reference store; no hallucinated sources.

## Milestone 5 — CSL citation mode

- pinned CSL processor/style assets;
- citation content blocks;
- formatted citation and system-owned bibliography;
- manifest and BibTeX/RIS exports;
- citation report UI.

Exit: APA output deterministic and source-traceable, clearly non-managed.

## Milestone 6 — Advanced structural safety

- tables, custom headings, protected constructs;
- .NET OpenXmlValidator integration;
- canonical invariants;
- property-based tests;
- security hardening.

Exit: required fixture matrix passes.

## Milestone 7 — Legacy Mendeley adapter R&D

- collect official-plugin fixtures;
- implement raw/parsed preservation;
- controlled add/edit/remove adapter;
- bibliography behavior;
- Word/Mendeley qualification gate.

Exit: capability enabled only for qualified fixture families.

## Milestone 8 — Modern Mendeley Cite adapter R&D

- discover actual package structures across versions;
- implement separate adapter if technically supportable;
- full qualification.

Exit: honest supported matrix; fallback remains available.

## Milestone 9 — Production deployment

- private deployment configuration;
- external storage optional;
- auth/rate limits/TTL deletion;
- monitoring and backup policy;
- user documentation.

## Build rule

Do not skip directly to native citation writing before milestones 1–6. A visually correct citation string is not proof of structural compatibility.
