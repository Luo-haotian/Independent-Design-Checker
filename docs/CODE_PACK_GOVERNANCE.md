# Code-Pack Governance

## Default Hong Kong Review Profile

The default is `hk-report-declared-default`, a selection profile rather than an engineering rule pack. IDC first reads the design codes stated in the submitted report and records all detected HK, BS, EN, GB, and other references. The Hong Kong profile provides review context only when the report is silent; it never silently selects the Concrete Code.

The implemented concrete adapter is separately versioned as `hk-bd-concrete-2020-amd-2024-04`: Hong Kong Buildings Department, *Code of Practice for Structural Use of Concrete 2013 (2020 Edition)*, with February 2022, June 2023, and April 2024 amendments. It activates only when that basis is unambiguous or reviewer-pinned. A project does not silently migrate when a new amendment is published.

## Manifest Requirements

Each pack records ID, jurisdiction, authority, title, edition, amendments, effective date, rule-set version, supported rule IDs, official URLs, source filenames, SHA-256 hashes, limitations, and engineering-approval state. Raw official PDFs are not committed.

## Approval Workflow

1. Obtain source documents from the authority's official website.
2. Store them in the controlled external code library and verify manifest hashes.
3. Map clauses, equations, tables, applicability, units, boundaries, and amendment effects.
4. Create sanitized golden cases and independent hand calculations.
5. Obtain documented approval from the responsible structural engineer.
6. Change `engineering_approved` only in a reviewed commit and record the approver/evidence in the pull request.

The v0.17 HK beam rules are intentionally `engineering_approved: false`. Their clause mapping and formula implementation must not be represented as certified until step 5 is complete.

## Other Jurisdictions

External packs may be supplied through `IDC_CODE_PACK_PATH`. Their jurisdiction must match a reviewer-pinned `--jurisdiction`; validation failure stops the run. Auto mode preserves report-declared foreign standards without applying HK rules. A custom pack must not reuse HK rule IDs or imply HK authority, and a deterministic adapter must be installed before it can produce engineering results.

## Copyright and Confidentiality

The public repository contains metadata and sanitized fixtures only. Official code PDFs, confidential submissions, private workbooks, and opaque spreadsheet UDF logic remain external.
