# IDC Workflow

This workflow shows how IDC is used today across desktop EXE, command line, and intranet server modes. The same review engine is reused where possible so report quality stays consistent across entry points.

```mermaid
flowchart TD
    A[User has a structural PDF submission] --> B{Choose entry point}

    B --> C[Desktop EXE: IDC_GUI.exe or IDC_GUI_OCR.exe]
    B --> D[Command line: main.py or main_ocr.py]
    B --> E[Intranet server: browser upload page]

    C --> F[Select PDF, review type, output folder, OCR mode if needed]
    D --> G[Pass PDF path, review type, output folder, OCR flags]
    E --> H[Upload PDF, choose Building or Temporary, choose OCR mode]

    H --> I[Server validates upload, access token, size, and OCR option]
    I --> J[Server stores upload in protected upload folder]

    F --> K{Readable text layer?}
    G --> K
    J --> K

    K -->|Yes| L[Extract text with PyMuPDF]
    K -->|No or forced OCR| M[Render PDF pages and run Tesseract OCR]

    L --> N[Normalize extracted submission content]
    M --> N

    N --> O[Build IDC prompt for Building or Temporary works]
    O --> P[Call configured Grok model]
    P --> Q[Generate structured IDC review content]
    Q --> R[Create branded Word report with cover, metadata, TOC, and comments]

    R --> S{Delivery mode}
    S -->|Desktop or CLI| T[Save report to local output folder]
    S -->|Intranet server| U[Show job status and provide report download link]

    T --> V[Reviewer checks, edits, and issues report]
    U --> V

    W[IT administrator] --> X[Install Python, server requirements, Tesseract, and .env]
    X --> Y[Start server with run_server.bat or Windows startup task]
    Y --> E

    Z[QA Records Batch Checker] --> AA[Upload OP / mill cert / cube test / reinforcement test packages]
    AA --> AB[AI extracts key fields and flags missing or non-conforming records]
    AB --> AC[Export register and exception list for project QA review]
```

## Current Operating Modes

- Desktop EXE mode remains the fastest path for personal testing and one-off local reviews.
- OCR EXE mode is used when PDFs are scanned or image-heavy.
- Intranet server mode lets staff upload from a browser while OCR and report generation run on the company server.
- CLI mode remains useful for repeatable testing and batch scripts.
- QA Records Batch Checker mode is used for batch registration of OP records, mill certificates, concrete cube tests, reinforcement tests, and similar QA records.

## Recommended Team Workflow

1. Staff or reviewer receives a PDF submission.
2. If working individually, use the desktop EXE.
3. If staff should avoid local installation, use the intranet server.
4. IDC extracts text or OCR content, calls the configured model, and generates a Word report.
5. A qualified reviewer checks the report, edits wording or findings where needed, and issues it through the normal project approval process.
6. IT maintains server configuration, API keys, Tesseract installation, access control, and retention of uploaded documents.

## QA Records Batch Workflow

1. Staff collects OP records, mill certificates, concrete cube tests, reinforcement tests, or a ZIP package of PDFs.
2. Staff opens the server `QA Records Batch Checker` page.
3. The server extracts PDF text or OCR content.
4. AI classifies each record and extracts register fields.
5. The server exports:
   - `qa_register.csv`
   - `qa_exceptions.csv`
   - `qa_raw_results.json`
   - `qa_summary.txt`
6. A QA/QC reviewer checks the register and exceptions before project acceptance.
