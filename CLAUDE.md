# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

An Odoo 19 Enterprise development workspace — not a single application repo.

| Path | What it is |
|---|---|
| `odoo-19.0+e.20260807/` | Vendored Odoo core + enterprise source. **Third-party code — read for reference, never modify.** Gitignored. |
| `odoo-19.0+e.20260807/odoo/addons/` | ~1470 core and enterprise modules. The best reference for how to build anything — imitate these. |
| `odoo-19.0+e.20260807/venv/` | Python 3.14 virtualenv. Must be active for every command. |
| `custom_addons/` | Project modules. **This is where development happens.** |
| `odoo.conf` | Local server config. Gitignored (contains machine-specific paths). |

Each module under `custom_addons/` may have its own `CLAUDE.md` with module-specific notes. Read it before working on that module.

## Running the server

Always activate the venv first:

```bash
source ~/odoo/odoo-19.0+e.20260807/venv/bin/activate
```

Then use the `odoo` console script with an **absolute** config path:

```bash
odoo -c ~/odoo/odoo.conf -d <database> --http-port=8069
```

Use `odoo`, not `python setup/odoo`. The relative form breaks depending on
the current directory and can pick up the wrong interpreter if the venv
isn't active. The console script lives inside the venv, so it fails loudly
instead of silently misbehaving.

## Install, upgrade, test

**Always pass `--stop-after-init` for install/upgrade/test runs.** Without it
Odoo starts an HTTP server and never exits — a background task waiting for
the process to finish will hang until it times out.

```bash
# First install into a new database
odoo -c ~/odoo/odoo.conf -d <db> -i <module> --stop-after-init

# After changing code or data — this is the normal iteration loop
odoo -c ~/odoo/odoo.conf -d <db> -u <module> --stop-after-init

# Run tests
odoo -c ~/odoo/odoo.conf -d <db> -u <module> --test-enable --stop-after-init

# Filter tests
--test-tags /<module>:TestClassName.test_method
```

`-u` against an existing database takes seconds; `-i` on a fresh one takes
minutes. Use `-i` only when the manifest's dependency list changes or when
verifying a clean install.

**Auto-reload does not migrate the schema.** `--dev=xml,reload` (set in
`odoo.conf`) reloads Python and XML, but any change to a *field definition* —
new field, changed type, new model — needs a `-u` run. Symptom of forgetting:
`psycopg2.errors.UndefinedColumn: column ... does not exist` on a field you
just added.

## Verification standard

**Test the way a user would, not the way the code expects.**

Modules routinely create their own stages, teams, tags and activity types,
then rely on records landing on them. Verification built from hand-constructed
records will pass while the feature is unreachable through the UI — a real
defect class found in this project (see `crm_gp_defect_log.md`, D-019).

Before claiming a feature works:
1. Create the record through the normal UI path with no manual setup.
2. Confirm the automation fires without intervention.
3. Confirm a **fresh** install works: `-i` on a brand-new database, then grep
   the log for `ERROR`, `CRITICAL`, `Traceback`.

Don't claim end-to-end verification that wasn't done end-to-end.

## Environment gotchas

These bit us once and will bite again:

- **PyPDF2 must be `<3.0`.** Odoo 19's `sale` module calls
  `cloneReaderDocumentRoot`, removed in PyPDF2 3.0. Symptom: sending a
  quotation raises `DeprecationError` from deep inside `mail_template.py`.
  Fix: `pip install "PyPDF2<3.0"`.
- **inotify watch limit.** `--dev=reload` watches ~1470 addon directories.
  Symptom: `ERRNO=28 No space left on device` at startup — this is the watch
  limit, not the disk. Fix: raise `fs.inotify.max_user_watches`, or drop
  `reload` from `dev_mode` and restart manually after Python changes.
- **Odoo's default admin has no email address.** Any cron guarded by
  `if not recipient.email: return` will silently do nothing. Set an email on
  user 2 before testing anything that sends mail.
- **Editable install noise.** `addons path is not a directory:
  __editable__...__path_hook__` on every start is harmless — an artifact of
  `pip install -e .`.
- **Python 3.14.** Newer than Odoo 19 targets. If a library raises something
  strange that isn't in Odoo's own code, the Python version is a plausible
  suspect.

## Odoo architecture notes

- Modules are Python packages with a `__manifest__.py` declaring dependencies,
  data files, and metadata. Behaviour is often driven as much by XML/CSV data
  files as by Python.
- Models subclass `odoo.models.Model` with declarative fields; the ORM
  generates the schema and handles CRUD, security, and translations.
- Views, actions, menus, security (`ir.model.access.csv`, record rules), and
  data records live in XML/CSV loaded per the manifest's `data` list.
- **Prefer configuration over code.** Odoo has native machinery for most
  things — automation rules, `ir.cron`, rule-based assignment, activity
  chaining via `mail.activity.type.triggered_next_type_id`. Reimplementing
  these in Python is usually the wrong call.
- Controllers live under `controllers/`, registered via
  `odoo.http.Controller` / `@route`.
- Client-side JS/CSS lives under `static/src/`, bundled via manifest `assets`
  entries — Odoo's own bundler, not a separate frontend build.
- `odoo scaffold <name> custom_addons/` generates a module skeleton.

## Conventions

- **Namespace everything.** External IDs, cron names, automation rule names
  and activity types carry the module prefix, so it's obvious which module
  owns a record.
- **Don't modify other developers' modules.** In this project that means
  `l10n_ao`, `zoom_tax_slab`, `bi_birthday_reminder`, `ai_claude`.
- **No credentials or client data** in any tracked file.
- **Placeholders over guesses.** When a requirement leaves something
  undefined (a person, a threshold, a recipient), use an
  `ir.config_parameter` with a safe default and flag it — don't invent a
  value.
- **Record what was assumed, skipped, or left open** in the commit message,
  under its own heading. Not scattered through prose.

## Git

- One branch per piece of work: `feature/<module>` for new modules,
  `fix/<module>-<topic>` for fixes. Merge to `main` when reviewed.
- `main` means *current known state*, not *finished*. See `KNOWN_ISSUES.md`
  for what's merged but incomplete.
