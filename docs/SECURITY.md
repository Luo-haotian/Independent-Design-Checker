# Security and Engineering Limitations

## Server Controls

- Configure a strong `IDC_SERVER_ACCESS_TOKEN` and `IDC_SERVER_SECRET_KEY`.
- The access token is accepted at login or in the `X-IDC-Token` API header; it is never accepted from URL query parameters or upload forms.
- Browser writes require a session CSRF token. Approval/rejection and fact edits require reviewer name and reason; fact edits also require replacement evidence.
- Upload size is capped by Flask. ZIP processing caps member count, member size, total expanded size, and compression ratio, flattens names into a controlled directory, and rejects duplicate output names.
- Raw uploads and reports expire after the configured retention period. SQLite audit metadata is not part of raw-file cleanup.

TLS and central identity management are deployment responsibilities. The built-in token/session flow is intended for a controlled internal service, not an internet-facing multi-tenant platform.

## Engineering Limitations

IDC v0.17 is decision support. It is not a substitute for a competent structural engineer, independent calculation, authority submission review, or professional sign-off. The included HK rule pack remains pending responsible engineer approval.

AI observations may be incomplete or incorrect. Only deterministic rules produce `PASS`/`FAIL`, and those results are valid only for their declared scope and inputs. Missing evidence, conflicting values, unsupported units, out-of-scope geometry/actions, and unapproved rule mappings must be resolved by a human reviewer.

## Secrets and Local Material

Never commit `.env`, access tokens, API keys, official code PDFs, confidential PDFs, uploads, reports, logs, company workbooks, or private calculation logic. The preservation archive records `.env` presence only and excludes its contents.
