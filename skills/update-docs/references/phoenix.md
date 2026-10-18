# Repo type: phoenix

## Where docs live

`README.md` at the root, module docs via `@moduledoc`/`@doc` attributes
(rendered by ExDoc into `doc/` -- not usually committed; check
`mix.exs`'s `docs/0` for the `main` page and `extras` list, which often
point at `guides/*.md` or a top-level `CHANGELOG.md`/`guides/` folder).

## What's generated, and by what

The `doc/` directory (ExDoc's HTML output) is always generated --
`mix docs`. Never hand-edit it; edit the `@moduledoc`/`@doc` attributes
or the `extras` Markdown files ExDoc assembles, then regenerate.

## What's public (must be documented)

Any module without `@moduledoc false`, and any public function
(`def`, not `defp`) without `@doc false`. Phoenix-specific surfaces:
routes in `router.ex`, LiveView events a template or JS hook calls, and
context functions called from outside their own context module.

## "Don't document" markers

`@moduledoc false` on a module, `@doc false` on a function, or a `defp`
(private function) — none of these belong in public docs.

## Breaking vs. routine for docs purposes

A changed route, a renamed/removed LiveView event, or a changed context
function's public signature is breaking. A new or renamed environment
variable read in `config/runtime.exs` needs an upgrade-notes mention, not
just a reference update.
