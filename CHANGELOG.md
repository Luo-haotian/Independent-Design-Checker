# Changelog

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
