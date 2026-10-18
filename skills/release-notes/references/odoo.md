# Repo type: odoo

## Detection

An `__manifest__.py` file (anywhere in the repo for a multi-module
addon tree, or at the root for a single module).

## Breaking

- A changed `depends` list in `__manifest__.py` (a module gained or lost a
  dependency other installs may rely on).
- A renamed or removed field on an existing model (breaks reports, exports,
  automations, and studio customizations that reference it by name).
- A removed or restructured view (`<record model="ir.ui.view">`) that other
  modules inherit from via `xpath`.
- A changed external ID (`id="..."` on a `<record>`) that other modules or
  data reference.

## Security

- Changed `ir.model.access.csv` rows (access rights per model/group).
- Changed or added `<record model="ir.rule">` entries (record rules —
  row-level security).
- Changed `groups_id` on a view or field, changing who can see or edit it.

## Upgrade notes

- A new file under `migrations/<version>/` means the operator must run
  `-u <module>` (or `--update=<module>`) to apply it, not just restart.
- The manifest's `version` key is the release boundary for this module —
  use it (not an arbitrary git tag) as `<version>` in the heading when the
  repo is a single addon.

## Examples

- Breaking: "Removed the `partner_ref` field from `res.partner`; use
  `ref` instead (#88, 3af1c9d)."
- Security: "Restricted `sale.order` write access to the `Sales / Manager`
  group; salespeople can no longer edit confirmed orders (#91, 0ab12cd)."
- Upgrade notes: "Added `migrations/17.0.1.1/pre-migrate.py`; run
  `-u sale_custom` to apply (#95, 55de321)."
