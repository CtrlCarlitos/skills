# Repo type: docs

There's no reliable file signature for a docs repo either — it could be
anything from a plain Markdown tree to a static-site generator. Select it
explicitly via `.release-notes/` or your own user config, the same as
`course`.

## Detection

None. Set explicitly in a repo or user override.

## Breaking

- A moved or renamed page: any URL change breaks inbound links,
  bookmarks, and search-engine results pointing at the old path.
- A removed page with no redirect.
- A restructured navigation/sidebar that changes where readers expect to
  find something (less severe than a broken link, but worth a note if
  it's disruptive).

## Security

Rarely applicable, unless the docs themselves document credentials,
tokens, or security-sensitive configuration that changed.

## Upgrade notes

Rarely applicable, unless the docs site itself has a build toolchain
readers run locally (e.g. a static-site generator version bump).

## Examples

- Breaking: "Moved `/guides/setup` to `/getting-started/setup`; add a
  redirect if you link to the old path (#30, aa1bb2c)."
- Fixed: "Corrected the `--config` flag example, which showed a removed
  option (#33, dd4ee5f)."
- Added: "New guide: 'Migrating from v1 to v2' (#35, ff6aa7b)."
