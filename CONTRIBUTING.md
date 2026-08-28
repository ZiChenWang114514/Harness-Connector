# Contributing

Harness Connector keeps each session adapter independent while sharing repository-level validation and documentation.

## Add or update a skill

1. Keep the existing Skill ID and public command interface stable.
2. Place the complete snapshot under `skills/<skill-id>/`.
3. Add or update its record in `catalog/skills.json`.
4. Run `python tools/generate_catalog.py --write`.
5. Run the aggregate checks and the adapter's own test suite.
6. Document source and verification changes in `docs/import-report.md` and `CHANGELOG.md`.

Use `tools/sync_from_sources.py --apply --skill <skill-id>` for an explicit import from a recorded public repository. Inspect the resulting diff before committing.

## Compatibility

Do not rename existing skills, silently change command names, or move adapter-specific runtime behavior into a shared package. Additive interface improvements should include tests and bilingual documentation.

## Credentials and test data

Never commit API keys, authentication tokens, complete private session transcripts, machine-specific logs, or personal absolute paths. CI must use mocked subprocesses and credential-free fixtures.
