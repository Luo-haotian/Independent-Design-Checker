# Changelog

## v0.16 - Contractor Submission Batch Review Enhancements

- added selectable Grok/Kimi API provider support while keeping Grok as the default provider
- added Kimi/Moonshot OpenAI-compatible environment configuration
- added provider selection to the desktop GUI, OCR GUI, and intranet server upload pages
- expanded QA batch register outputs with OCR diagnostics for scanned submissions
- added `qa_operator_report.md` to the QA output ZIP for step-by-step operator review
- added a contractor submission sample harness for real scanned Batch 15/16 samples and public electronic PDF samples
- added Dockerfile, Docker Compose, and Docker deployment guide for one-computer intranet hosting
- changed EXE packaging so real `.env` is not copied into `dist` unless `--include-env` is explicitly used

## v0.15 - QA Records Batch Checker

- added `docs/WORKFLOW.md` with the IDC desktop, CLI, OCR, and intranet server workflow
- added `docs/PRD.md` as the central product requirements document for product scope, version tracking, and roadmap
- added a QA Records Batch Checker MVP for OP, mill certificates, concrete cube tests, reinforcement tests, and similar QA records
- added multi-file/ZIP QA upload, AI extraction, CSV register output, exception CSV output, raw JSON output, and summary output
- updated the README project structure to include product workflow and PRD documents

## v0.14 - Intranet Server Release

- added a Flask/Waitress-based intranet upload server so staff can submit PDFs from a browser
- moved OCR-heavy processing to the server flow through the existing `CheckerOCR` pipeline
- added job status pages, report download links, upload size limits, optional access token protection, and basic health checks
- added IT-oriented `.bat` scripts for server install, server startup, and optional Windows startup task registration
- added `requirements_server.txt` and `docs/IT_SERVER_DEPLOYMENT.md` for company server deployment
- added configurable Tesseract command and OCR language settings through environment variables
- updated docs and runtime templates for server-side OCR deployment

## v0.12 - Sample-Style Word Report Release

- added a dedicated Word report generator that produces sample-inspired IDC report layouts
- introduced branded report assets for cover pages, headers, and submission blocks
- extracted project title, checked item, and job reference from source PDFs to populate report metadata
- improved temporary works and building prompts so reports include denser, more actionable IDC reviewer comments
- updated the GUI flow and packaged runtime so the distributed app continues working with `.env` beside the executable
- kept the project history additive through normal commits and version tagging instead of overwrite-style updates

## v0.11 - Cleanup and Documentation Alignment

- standardized the project as Grok-only
- removed legacy multi-provider references from source and docs
- fixed garbled text in docs and GUI status messages
- aligned OCR implementation, docs, and build flow around `Tesseract + pytesseract`
- simplified `.env.example` and runtime configuration
- removed outdated presentation and ad hoc test files from the main repo
- added a concise end-user guide in `docs/USER_GUIDE.md`
- refreshed the README to focus on the standard `IDC_GUI` workflow first

## v0.1 - Initial Public Source Release

- published the first source version of IDC
- included standard GUI, OCR GUI, CLI, and OCR CLI tools
