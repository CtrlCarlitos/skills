# Repo type: odoo

## Where docs live

Each module's own `README.rst` (the Odoo Apps Store convention — OCA
modules use a multi-file `readme/` directory: `DESCRIPTION.rst`,
`INSTALL.rst`, `CONFIGURE.rst`, `USAGE.rst`, `ROADMAP.rst`, assembled into
`README.rst` by a generator). A top-level `docs/` for anything beyond a
single module's scope.

## What's generated, and by what

If a `readme/` directory exists alongside `README.rst`, the README is
generated from it (OCA's `oca-gen-addon-readme` or similar) -- edit the
`readme/*.rst` fragments, never `README.rst` directly.

## What's public (must be documented)

- Models and fields intended for other modules or end users: anything
  without a `_` prefix on the field/model name, and anything referenced
  by a view.
- Views (`ir.ui.view` records) that are the actual UI surface.
- `ir.model.access.csv` and `ir.rule` entries -- these ARE the
  documentation of who can do what; a doc that restates them risks
  drifting, so prefer linking to the file over duplicating its content.

## "Don't document" markers

A model/field name starting with `_` is implementation detail. A module
depending on another listed in `depends` only for a technical reason
(not user-facing) doesn't need its own doc section.

## Breaking vs. routine for docs purposes

A changed `depends` list, a renamed/removed field referenced by a view
or export, or a changed access rule is breaking for anyone relying on
the current doc.
