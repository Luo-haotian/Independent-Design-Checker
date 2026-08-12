# IDC Development Roadmap

## Release Goal

IDC v0.17 adds page-level evidence, versioned code packs, deterministic Hong Kong reinforced-concrete beam checks, and a signed human-review audit trail while preserving the existing desktop, CLI, OCR, server, QA batch, and Word-report workflows.

## Status Legend

- `Completed`: implemented, verified, and committed.
- `In Progress`: implementation or verification is active.
- `Planned`: accepted scope that has not started.
- `Blocked`: requires an external decision, credential, or engineering approval.

## Completed

- M01 - Preserved v0.16 artifacts and complete Git history in `C:\Users\11131\Documents\IDC-Archive\2026-08-12-v0.16-pre-clean`.
  - Archive evidence: 94 source records, 79 unique payload files, 1,060.61 MiB payload.
  - Verification: Git bundle and SHA-256 payload verification passed.
  - Cleanup: repository workspace reduced to approximately 0.5 MiB; `.env` remained ignored and was not archived.
  - Commit: `88d092a`.
- M02 - Added the `idc` package, public evidence/review contracts, page-preserving ingestion, page-aware LLM chunking, full coverage disclosure, and the optional non-authoritative critic pass.
  - Verification: Python static compilation and a three-page ingestion smoke test passed.
  - Commit: `61a2f6d`.
- M03 - Added the HK-default code-pack registry, source-hash verification, effective-date pinning, external code-library support, exact-jurisdiction validation, and deterministic evidence/conflict gates.
  - Verification: the HK pack and all four external local sources were hash-verified; an attempted non-HK selection failed without fallback.
  - Engineering status: rule mappings remain pending responsible structural engineer approval.
  - Commit: `f49ed66`.
- M04 - Implemented the deterministic normal-depth rectangular singly reinforced RC beam vertical slice.
  - Scope: applicability, flexural demand/capacity, required/provided tension steel, longitudinal reinforcement limits, shear stress/capacity, required/provided links, minimum links, and link spacing.
  - Traceability: every result records rule ID, citations, formula version, units, evidence pages, demand, capacity, utilisation, status, message, and limitations.
  - Interfaces: CLI, OCR CLI, and both desktop GUIs accept a pinned code pack, reviewer-confirmed beam-fact JSON, JSON export, and the optional critic toggle.
  - Verification: sanitized pass/fail, missing-evidence, conflict, deep-beam, boundary, and JSON loader cases passed locally.
  - Engineering status: formulas and scope remain pending responsible structural engineer approval.
  - Commit: recorded in the M04 milestone commit.

## In Progress

- M05 - Add persistent jobs, signed reviewer decisions, audit events, retention, and server security hardening.

## Planned

- M06 - Extend CLI, GUI, server, JSON, and Word outputs; add tests, CI, packaging verification, and documentation.
- M07 - Push the branch and open a draft pull request for review.

## Blocked

- Engineering certification of code clauses, formula implementations, and rule scope requires approval by the responsible structural engineer.
- GitHub Release publication and merge to `main` require explicit user approval after the draft pull request review.

## Post-v0.17 Backlog

- Deflection and crack-control checks.
- Torsion and combined shear-torsion checks.
- Deep-beam strut-and-tie workflow.
- Flanged, doubly reinforced, prestressed, and composite beam checks.
- Column, slab, punching-shear, wall, foundation, steel, and wind-rule packs.
- Curated and engineering-approved code packs for jurisdictions outside Hong Kong.

## Evidence Log

Milestone completion entries will include the commit ID, tests, build results, archive size, repository size, and remaining limitations.

- M03 acceptance evidence is recorded above. Public manifests contain source hashes and official URLs, while raw code PDFs remain external through `IDC_CODE_LIBRARY`.
