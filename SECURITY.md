# Security

Droit processes legal documents and may handle personal data.

- Uploads are anonymized before indexing and external generation.
- Original PII mappings are encrypted at rest.
- Response de-anonymization is opt-in, role-restricted to analysts and admins, and recorded in `audit_logs`.
- LLM API keys are encrypted before persistence and are never returned by the API.
- Set `DROIT_PII_ENCRYPTION_KEY` and `DROIT_JWT_SECRET` in production.
- Never commit `.env`, `storage/.pii.key`, uploaded files, passwords, or provider tokens.
- Revoke any credential that appears in a terminal command, issue, log, or chat transcript.

Report security issues privately to the repository owner rather than opening a public issue.
