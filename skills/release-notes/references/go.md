# Repo type: go

## Detection

A `go.mod` file at the repo root (or the module root being described).

## Breaking

- A removed or changed-signature exported identifier (function, method,
  type, field, or constant) — anything an external importer could
  reference.
- A new major version: the module path gains a `/vN` suffix (`/v2`,
  `/v3`, ...) per Go's module versioning rules.
- A changed `cmd/` flag: removed, renamed, or changed default that alters
  output or exit behavior.
- If `gorelease` or `golang.org/x/exp/cmd/apidiff` is installed, run it
  against the previous tag to confirm what's actually API-incompatible —
  don't rely on commit messages alone.

## Security

- A dependency bump in `go.sum` whose changelog or advisory lists a CVE
  fix.
- A fix to input validation, deserialization, or a crypto/`net/http`
  handler.

## Upgrade notes

- A `go` directive bump in `go.mod` (`go 1.24` → `go 1.25`) — states the
  new minimum Go toolchain version.
- A changed required environment variable or config flag for `cmd/`
  binaries.

## Examples

- Breaking: "`client.New` now requires a `context.Context` as its first
  argument (#201, 4acb910)."
- Security: "Bumped `golang.org/x/crypto` to fix CVE-2026-XXXXX in the
  SSH client (#205, e01fa22)."
- Upgrade notes: "Raised the minimum Go version to 1.23 in `go.mod`
  (#210, b2c3d44)."
- Deprecated: "`client.OldDial` is now `// Deprecated: use client.Dial`;
  it will be removed in a future major version (#198, 1a2b3c4)."
