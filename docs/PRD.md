# Product Requirement Document: Independent Design Checker

## 1. Product Summary

Independent Design Checker (IDC) is a structural engineering document review tool. It reads PDF submissions, extracts text or OCR content, asks an AI model to produce IDC-style review comments, and generates a structured Word report for building and temporary works submissions.

The product currently supports desktop EXE, command line, OCR, intranet server workflows, and a QA Records Batch Checker MVP. The long-term direction is to become a broader engineering document intelligence platform for design review, project QA records, and compliance registers.

## 2. Product Goals

- Reduce repetitive engineering document review time.
- Produce consistent IDC-style draft reports with project metadata, structured comments, and recommendations.
- Support both local reviewer workflows and company server deployment.
- Keep confidential submissions on controlled company machines where possible.
- Preserve human engineering judgment: IDC prepares draft outputs, while qualified reviewers approve final reports.

## 3. Target Users

- Structural engineers and IDC reviewers preparing draft review reports.
- Project engineers who need a first-pass document check.
- QA/QC and site teams who need document registers and exception lists.
- IT administrators who deploy the intranet server and manage runtime configuration.
- Managers who need visibility on document review status and future product scope.

## 4. Current Scope

### In Scope

- PDF upload or local PDF selection.
- Building and temporary works review types.
- Text extraction with PyMuPDF.
- OCR extraction with Tesseract and pytesseract.
- Grok API analysis through `.env` configuration.
- Branded Word report generation.
- Desktop GUI and OCR GUI.
- CLI and OCR CLI.
- Intranet server upload, job status, and report download.
- QA Records Batch Checker for OP records, mill certificates, concrete cube tests, reinforcement tests, and similar PDF QA records.
- CSV register, CSV exception list, raw JSON, and summary output for QA batches.
- IT deployment scripts and guides.

### Out of Scope For Current Version

- Final professional certification or automatic engineering approval.
- Direct public internet hosting.
- Multi-user authentication beyond optional access token.
- Full document management system replacement.
- Automatic validation against every project-specific code, contract, or material specification.

## 5. Version Register

| Version | Status | Summary |
| --- | --- | --- |
| v0.1 | Released | Initial public source release with standard GUI, OCR GUI, CLI, and OCR CLI. |
| v0.11 | Released | Cleanup release; standardized Grok-only configuration, refreshed docs, and aligned OCR implementation. |
| v0.12 | Released | Added sample-style branded Word report generation, metadata extraction, and denser IDC reviewer comments. |
| v0.14 | Released | Added intranet server deployment so staff can upload PDFs in a browser while OCR and report generation run on the server. |
| v0.15 | Released | Adds product workflow documentation, this PRD, and a QA Records Batch Checker MVP for batch QA register extraction. |
| v0.16 | Released | Adds Grok/Kimi provider selection, contractor submission operator reports, OCR diagnostics, sample validation, and Docker intranet deployment. |

## 6. Functional Requirements

### 6.1 Desktop Review

- User can open an EXE, choose a PDF, select review type, and generate a Word report.
- User can choose OCR mode when using the OCR EXE.
- Reports are saved to the selected output folder.
- Desktop EXE should remain available because it is convenient for testing and individual review.

### 6.2 Command Line Review

- User can run `main.py` or `main_ocr.py` with file path, review type, output folder, model override, and OCR flags.
- CLI should remain stable for regression testing and scripted workflows.

### 6.3 Intranet Server Review

- Staff can open an intranet URL in a browser.
- Staff can upload a PDF and choose review type and OCR mode.
- Server validates upload type, size, access token, and OCR option.
- Server performs extraction, OCR, AI analysis, and report generation.
- Staff can monitor job status and download the generated Word report.
- IT can configure host, port, access token, upload directory, report directory, worker count, OCR language, and Tesseract path through `.env`.

### 6.4 Documentation

- User guide explains normal staff workflows.
- IT guide explains installation, `.env`, Tesseract, firewall, startup task, and data retention.
- PRD records product purpose, scope, version history, planned modules, and future roadmap.
- Workflow document shows how desktop, CLI, and server modes connect.

### 6.5 QA Records Batch Checker

- Staff can upload multiple PDFs or a ZIP package through the intranet server.
- Supported record classes include OP, mill certificate, concrete cube test, reinforcement test, and other/unknown records.
- Server extracts text with PyMuPDF and uses OCR when required.
- AI classifies each document and extracts key register fields.
- Server outputs a downloadable ZIP containing:
  - `qa_register.csv`
  - `qa_exceptions.csv`
  - `qa_raw_results.json`
  - `qa_summary.txt`
- QA/QC reviewer must verify extracted values before official acceptance.

## 7. Non-Functional Requirements

- Uploaded files and reports must not be committed to git.
- Real API keys must remain in `.env` and outside version control.
- Server should bind to trusted intranet interfaces only unless protected by company infrastructure.
- OCR and AI calls may be slow; UI must show processing status.
- Report output should remain editable Word format.
- Installation scripts should fail visibly instead of closing silently.
- The system should favor conservative, auditable outputs over unsupported conclusions.

## 8. QA Records Batch Checker

### Request

Leadership wants AI to batch read and register project OP-related documents, mill certificates, concrete cube tests, reinforcement tests, and similar QA records.

### Product Fit

This is suitable for the IDC project as a related module rather than part of the current structural design report workflow. The shared capabilities are the same: upload documents, OCR, extract fields, classify records, identify missing information, and generate a register or exception report.

Product positioning:

- Current module: `Design Review Report Generator`
- New module: `QA Records Batch Checker`

This keeps the product coherent while avoiding confusion between engineering design checking and QA document administration.

### Why It Fits

- It reuses server upload, OCR, document parsing, AI extraction, and report/export infrastructure.
- It solves a real repetitive project workflow.
- It can produce auditable registers and exception lists, which are easier to review than free-form AI answers.
- It extends IDC from "single submission review" to "project document intelligence."

### Risks

- Material certificates and test reports have many vendor-specific layouts.
- AI extraction must be checked against source documents before acceptance.
- False positives and false negatives can affect compliance tracking.
- Project specifications differ, so pass/fail logic should be configurable.
- Confidential project records require stronger access control and retention policy.

### v0.15 MVP Scope

- Batch upload PDF files or a ZIP package.
- Classify each document as OP, mill certificate, concrete cube test, reinforcement test, or unknown.
- Extract core fields into a register:
  - project name or contract
  - supplier or laboratory
  - document type
  - certificate or report number
  - material type and grade
  - test date
  - delivery or pour date where available
  - batch, heat, bar mark, cube ID, or sample ID where available
  - result value and pass/fail text where available
  - source file and page reference
  - confidence level
  - missing fields
- Export an Excel or CSV register.
- Generate an exception report listing missing, duplicated, expired, unreadable, or potentially non-conforming records.

Implemented in v0.15:

- PDF and ZIP upload through the intranet server.
- AI classification and field extraction.
- CSV register output.
- CSV exception output.
- Raw JSON output.
- Summary text output.
- Downloadable ZIP package.

Deferred:

- Native `.xlsx` export.
- Reviewer edit screen.
- Duplicate checking across previous project records.
- Project-specific compliance rule packs.
- User login and approval audit trail.

## 9. Future Roadmap

### Near Term

- Add persistent job history to server mode.
- Add batch upload support for design review files.
- Add configurable retention cleanup for uploads and reports.
- Add clearer server startup diagnostics for IT.
- Add release packaging that preserves desktop EXE while adding server scripts.

### Medium Term

- Add Excel register export for certificates and test reports.
- Add project-specific field templates.
- Add reviewer correction workflow so extracted fields can be edited and approved.
- Add admin dashboard for job status, storage usage, and failed jobs.

### Long Term

- Add user authentication and role-based access.
- Add project workspace structure with document history.
- Add comparison between submissions and previous revisions.
- Add configurable compliance rule packs for different project requirements.
- Add integration with SharePoint, network drives, or document management systems.
- Add audit trail for AI extraction, reviewer edits, and final approval.

## 10. Open Questions

- Does "OP" mean Occupation Permit records, operational permits, or another project-specific document class?
- What register format does leadership expect: Excel, CSV, Word summary, or dashboard?
- Which fields are mandatory for each certificate and test type?
- What project specifications should pass/fail checks compare against?
- Should QA records be stored after processing, or deleted after export?
- Who is allowed to upload, review, approve, and download batch QA outputs?
# v0.17 Product Addendum

The product objective is trustworthy layered checking: document coverage, design-basis validation, evidence/conflict gating, deterministic engineering rules, non-authoritative AI observations, and signed human review. Hong Kong remains the default jurisdiction while exact-match external packs enable other countries without silent fallback.

The v0.17 release criterion is a traceable RC beam flexure/shear vertical slice, not broad code coverage. The authoritative scope and pending work are maintained in `docs/DEVELOPMENT_ROADMAP.md`.
