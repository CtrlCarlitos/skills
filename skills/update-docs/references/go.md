# Repo type: go

## Where docs live

Package-level doc comments (the comment directly above `package foo`,
and above each exported identifier) are the primary documentation --
rendered by `go doc` and pkg.go.dev. `README.md` at the module root for
anything `go doc` can't express (installation, examples that span
packages, project status).

## What's generated, and by what

Nothing is typically checked in as generated output here (unlike ExDoc
or rustdoc, `go doc` renders on demand, not to a committed file) --
exceptions: a `docs/api.md` produced by `gomarkdoc` or similar, which
should say so and be regenerated via that tool, not hand-edited.

## What's public (must be documented)

Every exported identifier (capitalized name): functions, types, methods,
fields, constants. `go vet` and `golint`/`staticcheck` already flag
missing doc comments on these -- treat an exported identifier with no
doc comment at all as a missing-doc finding, not just a stale one.

## "Don't document" markers

An unexported (lowercase) identifier. A file or identifier the package
doc comment explicitly calls internal/experimental.

## Breaking vs. routine for docs purposes

A removed or changed-signature exported identifier, or a new major
version (`/vN` module path), is breaking. A `go` directive bump in
`go.mod` (new minimum Go version) is an upgrade note. If `gorelease` or
`apidiff` is installed, use it against the previous tag to confirm what
actually changed before flagging something as breaking.
