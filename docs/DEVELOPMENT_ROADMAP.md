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
  - Interfaces: CLI, OCR CLI, and both desktop GUIs accept a jurisdiction, automatic or reviewer-pinned code basis, generic reviewed-fact JSON, JSON export, and the optional critic toggle. Member-specific facts are accepted only by a matching installed adapter.
  - Verification: sanitized pass/fail, missing-evidence, conflict, deep-beam, boundary, and JSON loader cases passed locally.
  - Engineering status: formulas and scope remain pending responsible structural engineer approval.
  - Commit: `f45069c`.
- M05 - Added SQLite run/fact/result/audit persistence, signed fact edits and decisions, 30-day raw-file retention, and server security controls.
  - Security: access tokens are exchanged at login and held in an HTTP-only same-site session; URL/form token propagation was removed; mutating routes require CSRF tokens.
  - Server: structured result download, fact-edit, and approval/rejection endpoints were added while preserving prior routes.
  - Archive uploads: member count, member size, total expanded size, compression ratio, duplicate output name, and path containment are validated.
  - Verification: restart persistence, audit history, required reviewer/reason, retention, traversal, duplicate-name, and ZIP-ratio cases passed locally.
  - Commit: `37ebce2`.
- M06 - Added controlled dependency inputs, Python 3.11/3.12 tooling, Windows/Linux CI, unit and design-action gates, security coverage, packaging controls, and English user/deployment/architecture/governance/security documentation.
  - Verification: 38 sanitized tests pass in an isolated Python 3.12.13 environment; `idc` package coverage is 86%; Ruff and `pip check` pass.
  - Packaging: all four executables build with PyInstaller 6.22.0 and pass CLI-help or GUI-startup smoke tests. The build log contains no missing-import, traceback, or deprecation tokens.
  - Commit: `a12977d`, with dependency correction in `39946b7`.
- M06b - Replaced the concrete-specific product default with report-declared multi-code resolution and removed member-specific UI emphasis.
  - Selection: report-declared HK, BS, EN, GB, and other standards are retained in source order. The general HK default is a selection profile, not a concrete code. Competing member codes require reviewer pinning; non-HK selection never falls back to HK.
  - Interfaces: desktop and server screens expose general jurisdiction, code basis, reviewed facts, evidence, results, critic, and human decision controls. The restricted RC member rules remain a separately versioned adapter and are not the UI identity.
  - Verification: mixed-basis, non-HK no-fallback, generic-fact, no-false-pass, and adapter-activation tests pass.
  - Commits: `39946b7`, `9e1a762`, `55c473b`, and `dbca38c`.
- M07 - Completed cross-platform CI and replacement release-candidate verification.
  - CI: GitHub Actions run `31562434478` passed on Windows and Linux with Python 3.11 and 3.12.
  - Release candidates: `C:\Users\11131\Documents\IDC-Archive\2026-08-12-v0.17-release-candidates`, 205.45 MiB. `release-candidate-inventory.json` records the four executable hashes, source commit, test evidence, embedded profiles, and limitations.
  - Cleanup: intermediate build/spec output, the isolated build environment, and superseded concrete-default/deprecated-import candidates were removed after verification.
  - Source commit: `dbca38c`.
- M08 - Added the calculation-first submission and human-report workflow.
  - Submission pages are classified as cover, contents, calculation, drawing, supporting or unknown before checking; drawing pages are deferred in v0.17.
  - Calculation/supporting/uncertain candidates are normalized and reviewed through shared Building or Temporary profiles, then merged into one structured comment set.
  - Local text-only Concrete, Foundation and Steel clause indexes validate candidate citations without allowing an HK-jurisdiction fallback.
  - The human Word report now contains review scope, executive summary, actionable comment schedule and overall notes; maintenance provenance is delivered in the Standard Package ZIP.
  - The Server shows review-mode guidance and classified page ranges, and provides both report and standard-package downloads.

## In Progress

- None.

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
- Final local verification: 38 tests passed, `idc` coverage is 86%, Ruff passed, dependency consistency passed, and all four executable smoke tests passed.
- Final packaging verification: both the general `hk-report-declared-default` selection profile and the separately versioned `hk-bd-concrete-2020-amd-2024-04` adapter manifest/rules are embedded. The real `.env` is absent.
- Preservation archive: `C:\Users\11131\Documents\IDC-Archive\2026-08-12-v0.16-pre-clean` is 1,060.78 MiB including indexes and verification material; its recorded unique payload is 1,060.61 MiB.
- Repository: public working files are 1,281,648 bytes (1.22 MiB), below the 10 MiB target. `.env`, raw code PDFs, build outputs, uploads, reports, and private comparison material remain excluded.
- Online record: the Buildings Department code index and main official PDF link were rechecked on 2026-08-12 and still provide the 2020 Edition plus the February 2022, June 2023, and April 2024 amendment record.
- The earlier concrete-default candidate set was explicitly superseded and deleted. The replacement prioritises every code stated by the submitted report and retains the general HK context only when the report is silent.
