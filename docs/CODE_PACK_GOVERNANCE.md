# Code-Pack Governance

## Default Hong Kong Basis

The default pack is `hk-bd-concrete-2020-amd-2024-04`: Hong Kong Buildings Department, *Code of Practice for Structural Use of Concrete 2013 (2020 Edition)*, with February 2022, June 2023, and April 2024 amendments. A project pins its pack and optional as-of date; it does not silently migrate when a new amendment is published.

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

External packs may be supplied through `IDC_CODE_PACK_PATH`. Their jurisdiction must match the requested `--jurisdiction`; validation failure stops the run. A custom pack must not reuse HK rule IDs or imply HK authority.

## Copyright and Confidentiality

The public repository contains metadata and sanitized fixtures only. Official code PDFs, confidential submissions, private workbooks, and opaque spreadsheet UDF logic remain external.
