# Active Plan

## Milestone: Harden drafting privacy, coverage, and export

### Goals

- Keep every value that leaves for a provider aliased, including prior clause context.
- Cover authentication, organization scoping, regeneration, export, and versions with API tests.
- Finish the drafting UI: draft list, version history, risk panel, organization templates.
- Ship a working PDF renderer and apply the drafting migration to the deployment database.

### Completed

**1. Regeneration privacy**

- `backend/app/core/drafting/generator.py` gained `anonymize_text`, which re-aliases restored
  values (case-insensitive, longest value first) before the prompt is built.
- `generate_clause` now aliases `prior_clauses` and the user-supplied `instruction`. Stored
  clause bodies hold restored values, so both were leaking original party names.
- The same path covers first-pass generation, because `_generate_all` feeds restored bodies
  forward as prior context.

**2. API integration tests** — `backend/tests/test_drafting_api.py`

- Authentication and organization scoping: anonymous template and draft reads return 401; a
  user seeded into a second organization sees an empty list and 404 on another organization's
  draft detail and export.
- Regeneration: asserts the clause version increments, the source returns to `generated`, and
  no input value appears in the recorded provider prompt.
- Export: anonymous export is 401, DOCX and PDF both render, an unknown format is 422, and two
  `draft_export` audit rows are persisted with their formats.
- Version snapshots: list, restore an earlier snapshot, and confirm the restore itself creates
  a new version; unknown versions are 404.
- Organization templates: create, list, update, builtin protection (403), validation (422), delete.

**3. Backend surface added**

- `GET /drafting/drafts/{id}/versions` and `POST /drafting/drafts/{id}/versions/{version}/restore`
  (audited as `draft_version_restore`); snapshots now carry rationale and risk notes.
- `POST|PUT|DELETE /drafting/templates` for admins, with slug generation, builtin protection,
  a 409 when drafts still reference the template, and audit events.
- `DraftTemplateRequest` validates labelled inputs and headed clause outlines.

**4. Defect found by the new tests**

- `create_draft` flushed the draft before appending clauses, so `draft.clauses` triggered a lazy
  load under asyncpg and every draft creation failed with `MissingGreenlet`. The draft now stays
  pending until its clauses exist.

**5. PDF export**

- `reportlab==4.2.5` (pure Python, no system libraries) added to `backend/requirements.txt`.
- `export_pdf` renders A4 with escaped title, clause headings, and justified paragraphs; the
  export route selects the media type and filename extension by format and drops the 501.

**6. Frontend**

- `src/lib/api.ts`: `getDraft`, `deleteDraft`, `listDraftVersions`, `restoreDraftVersion`,
  template create/update/delete, typed `DraftRiskBreakdown`, and `exportDraft(id, format, name)`.
- `DraftRiskPanel` (banded score, category totals, missing clauses, asymmetric and renewal terms).
- `DraftVersionHistory` (loading, empty, error states; restore with the current version marked).
- `DraftTemplateManager` (admin-only authoring of inputs and clause outline, edit, delete).
- Drafting route: draft list with reopen, close and delete, DOCX and PDF export, risk and version
  sidebar, and clause editors keyed by version so regenerated text replaces stale input state.

**7. Migration**

- `alembic upgrade head` applied locally; current revision is `a1d4e6f7b8c9`.

### Validation performed

- `.venv/bin/python -m pytest backend/tests -q` — 57 passed.
- `cd frontend && npm run lint && npm run build` — both clean.

### Remaining work

**A. Deployment migration**

1. Back up the deployment database.
2. Run `alembic current` against it to confirm the starting revision.
3. Run `alembic upgrade head` with `DROIT_DATABASE_URL` pointing at the deployment database.
4. Re-run `alembic current` and smoke test `GET /api/v1/drafting/templates`.

**B. Residual privacy gap**

- Values a user types directly into a clause body are not part of `inputs`, so they are not
  aliased on the next regeneration. Decide between running the existing Presidio anonymizer over
  clause bodies before they are sent, or warning in the editor that edited text is sent verbatim.
  Prefer the anonymizer path and add a test mirroring the prior-clause assertion.

**C. Coverage gaps**

- Audit assertions for `draft_template_create|update|delete` and `draft_version_restore`.
- A non-admin user asserting 403 on the template endpoints (requires seeding an analyst).
- A PDF content assertion stronger than the `%PDF-` header, for example clause headings extracted
  with the existing `pdfplumber` dependency.

**D. UI follow-ups**

- Regeneration instruction field; the API already accepts `instruction`.
- Confirmation before draft and template deletion.
- Surface the 409 template-in-use message distinctly from generic failures.
- Non-Latin text in PDF export needs a registered TrueType font; currently Helvetica only.

**E. Documentation**

- Add the versions, restore, and template endpoints to `docs/api-contracts.md`.
- Record the PDF renderer choice in `docs/decisions/` if reportlab is considered durable.

### Deferred

Pydantic AI orchestration, FastMCP, Redis, Celery, SSE, comparison, annotations, and marketing
content remain deferred until a concrete consumer or measured bottleneck justifies them.
