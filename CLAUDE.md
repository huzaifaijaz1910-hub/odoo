# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is an Odoo 19 (Enterprise) development workspace, not a single application repo:

- `odoo-19.0+e.20260807/` — the vendored Odoo core + enterprise source tree. Treat this as third-party code: read it for framework/API reference, but custom development should not modify it directly.
  - `odoo/` — the Odoo framework itself (ORM, HTTP layer, CLI, `addons/` containing ~1470 core/enterprise modules).
  - `setup/odoo` — the actual server entry point (equivalent to the classic `odoo-bin`; there is no `odoo-bin` at the repo root in this checkout).
  - `venv/` — a pre-built Python 3.14 virtualenv for running Odoo.
  - `requirements.txt` — pinned Python dependencies (version pinned per Python/OS combination).
- `custom_addons/` — where project-specific custom Odoo modules go. Currently empty; this is the directory to develop in.
- `odoo.conf` — server config used to run the local instance (db name `odoo19`, port 8069, addons_path pointing at both the core addons and `custom_addons/`).

## Running the server

Activate the venv, then start via the `setup/odoo` entry point with the config file:

```bash
source odoo-19.0+e.20260807/venv/bin/activate
python odoo-19.0+e.20260807/setup/odoo -c odoo.conf
```

Common flags (appended to the command above):
- `-u <module,...>` / `--update` — upgrade specific modules (needed after changing a module's code/data in `custom_addons/`).
- `-i <module,...>` — install specific modules.
- `--stop-after-init` — run the given install/update/test operation then exit, without starting the HTTP server (use this for module install/update/test runs from the CLI).
- `--test-enable` / `--test-tags` / `--test-file` — control which tests run.
- `--dev=xml,reload` — already set in `odoo.conf` for local dev (auto-reloads XML/Python on change).

## Testing

Odoo tests are run through the server process itself, scoped to a database and module(s), e.g.:

```bash
python odoo-19.0+e.20260807/setup/odoo -c odoo.conf -d odoo19 -u <your_module> --test-enable --stop-after-init
```

Use `--test-tags` to filter to specific test classes/methods/tags (e.g. `--test-tags /your_module:TestClassName.test_method`).

## Architecture notes (Odoo framework)

- Modules are self-contained Python packages under an addons path (`odoo/addons/` for core/enterprise, `custom_addons/` for project modules), each with a `__manifest__.py` declaring dependencies, data files, and metadata.
- Business objects are declared as ORM models (`odoo.models.Model` subclasses) using declarative fields (`odoo/fields.py`); the ORM auto-generates the DB schema and handles CRUD, security, and translations.
- Views, actions, menus, security rules (`ir.model.access.csv`, record rules), and demo/data records are defined in XML/CSV data files loaded per the manifest's `data`/`demo` lists — module behavior is often driven as much by these data files as by Python code.
- HTTP/controllers live under each module's `controllers/`, registered via `odoo.http.Controller`/`@route`; web/portal/website behavior builds on this layer.
- The `odoo/cli/` package provides subcommands (`server`, `shell`, `scaffold`, `db`, `i18n`, `populate`, etc.) invoked through `setup/odoo <subcommand>`; `scaffold` generates a new module skeleton (useful when starting a new module under `custom_addons/`).
- Client-side JS/CSS for a module lives under that module's `static/src/`, bundled via manifest `assets` entries (Odoo's own asset-bundling, not a separate frontend build tool).


Odoo CLI notes:
- Always use --stop-after-init for install/upgrade runs; otherwise the process
  starts a web server and never exits.
- Install: odoo -c ~/odoo/odoo.conf -i module_name --stop-after-init
- Upgrade after code changes: -u instead of -i
- Run the dev server separately in its own terminal

crm_gp installed successfully in crm_gp_test2. For future changes use
-u crm_gp --stop-after-init against that database, not a fresh -i.