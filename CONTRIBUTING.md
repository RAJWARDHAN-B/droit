# Contributing

## Workflow

1. Read the applicable `AGENTS.md` and `PLAN.md`.
2. Make the smallest change that satisfies the task.
3. Add or update focused tests.
4. Run backend or frontend validation before opening a review.
5. Update documentation when behavior, configuration, or schema changes.

## Database changes

Create an Alembic migration for every schema change. Do not commit local database files, uploaded documents, provider keys, or encryption keys.

## Pull requests

Describe the behavior changed, security implications, migrations, and validation performed. Keep unrelated formatting and refactors out of the change.
