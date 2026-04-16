# Postgres init scripts

Every `.sql` / `.sh` file in this directory runs in lexical order the **first
time** the `wfdos-postgres` Docker volume is created (and only then). These
are Docker Postgres's standard init-script mechanism.

## Current scripts

- `00-extensions.sql` — enables the `vector` extension (pgvector) so
  `skills.embedding_vector` can be added to the canonical schema later.

## What goes here next (open work)

Once the canonical schema is designed (see
`docs/database/wfdos-schema-inventory.md`), add:

- `10-schema.sql` — `CREATE TABLE` statements for all 30+ wfd-os tables.
- `20-reference-data.sql` — static lookup tables (cip_codes, soc_codes,
  etc.) seeded with canonical values.
- Optional `30-fixtures.sql` — tiny fake dataset for smoke testing.

Keep the files idempotent (`CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO
NOTHING`) so re-running against an existing volume doesn't error.

## Regenerating from scratch

```bash
docker compose -f docker-compose.dev.yml down -v   # nukes the volume
docker compose -f docker-compose.dev.yml up -d     # re-runs all init scripts
```
