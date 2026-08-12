# IDC Development Roadmap

## Release Goal

IDC v0.17 adds page-level evidence, report-declared multi-code basis resolution, extensible deterministic checking adapters, and a signed human-review audit trail while preserving the existing desktop, CLI, OCR, server, QA batch, and Word-report workflows.

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
- M03 - Added a general HK report-declared default profile, source-hash verification, effective-date pinning, external code-library support, exact-pack validation, and deterministic evidence/conflict gates.
  - Verification: the HK pack and all four external local sources were hash-verified; an attempted non-HK selection failed without fallback.
  - Engineering status: rule mappings remain pending responsible structural engineer approval.
  - Commit: `f49ed66`.
- M04 - Implemented the first small deterministic adapter for a normal-depth rectangular singly reinforced RC member vertical slice.
  - Scope: applicability, flexural demand/capacity, required/provided tension steel, longitudinal reinforcement limits, shear stress/capacity, required/provided links, minimum links, and link spacing.
  - Traceability: every result records rule ID, citations, formula version, units, evidence pages, demand, capacity, utilisation, status, message, and limitations.
  - Interfaces: CLI, OCR CLI, and both desktop GUIs accept a pinned code pack, reviewer-confirmed beam-fact JSON, JSON export, and the optional critic toggle.
  - Verification: sanitized pass/fail, missing-evidence, conflict, deep-beam, boundary, and JSON loader cases passed locally.
  - Engineering status: formulas and scope remain pending responsible structural engineer approval.
  - Commit: `f45069c`.
- M05 - Added SQLite run/fact/result/audit persistence, signed fact edits and decisions, 30-day raw-file retention, and server security controls.
  - Security: access tokens are exchanged at login and held in an HTTP-only same-site session; URL/form token propagation was removed; mutating routes require CSRF tokens.
  - Server: structured result download, fact-edit, and approval/rejection endpoints were added while preserving prior routes.
  - Archive uploads: member count, member size, total expanded size, compression ratio, duplicate output name, and path containment are validated.
  - Verification: restart persistence, audit history, required reviewer/reason, retention, traversal, duplicate-name, and ZIP-ratio cases passed locally.
  - Commit: `37ebce2`.

## In Progress

- M06b - Replace the concrete-specific product default with report-declared HK/BS/EN/GB code-basis resolution, remove member-specific UI emphasis, rerun tests, and rebuild release candidates.
- M07 - Fix the Python 3.11 dependency constraint, push the correction, and observe the next GitHub Actions run on draft PR #1.

## Planned

- Add an inline desktop fact editor and deterministic recheck action. v0.17 currently uses reviewer-confirmed JSON in desktop apps and structured fact-edit APIs on the server.
- Add broader mocked-provider end-to-end coverage for scanned PDFs, all GUI interactions, and server worker restart/resume behaviour.

## Blocked

- Engineering certification of code clauses, formula implementations, and rule scope requires approval by the responsible structural engineer.
- Docker image execution is not verified on this host because the Docker CLI is unavailable; Dockerfile and Compose configuration are updated for CI or another host.
- Representative DOCX package/XML/content verification passed, but visual raster verification remains blocked because the bundled renderer has no LibreOffice and Microsoft Word automation did not complete conversion on this host.
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
- M06 completed: added controlled dependency inputs, Python 3.11/3.12 Windows/Linux CI, unit conversion and ULS/action/scope evidence gates, JSON/Word parity tests, server security tests, deployment updates, and English architecture/governance/security/user documentation.
  - Verification: 31 sanitized tests pass on Python 3.12.13; `idc` package coverage is 85%; Ruff and `pip check` pass.
  - Packaging: all four executables built with PyInstaller 6.22.0, embedded the HK manifest/rules, and passed CLI-help or GUI-startup smoke tests.
  - Release candidates: `C:\Users\11131\Documents\IDC-Archive\2026-08-12-v0.17-release-candidates`, 205.41 MiB, with per-file SHA-256 inventory. Build/spec directories and all stale build attempts were removed.
  - Repository: public working files are approximately 0.33 MiB; `.env`, raw code PDFs, build outputs, uploads, reports, and private comparison material are excluded.
  - Online record: the Buildings Department code index and main official PDF link were rechecked on 2026-08-12 and still list the 2020 Edition with February 2022, June 2023, and April 2024 amendments.
  - Commit: recorded in the M06 milestone commit.
- The first M06 candidate set and CI result were superseded after product review identified that a concrete-specific default and member-specific UI emphasis were inappropriate. The replacement uses the general HK report-declared profile and prioritises every code stated by the submitted report; final candidate hashes will be replaced after rebuild.
