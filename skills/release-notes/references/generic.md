# Repo type: generic

The fallback type. Use it when no other built-in type's detection matches,
and no repo or user override applies.

## Detection

No file signature; this is the default when nothing else is detected.

## Breaking

- A removed or renamed public API, CLI flag, config key, or environment
  variable.
- A changed default value that changes behavior for existing users.
- A changed on-disk or network format that older clients/readers can't
  parse.

## Security

- Any fix the commit message, PR, or diff identifies as addressing a
  vulnerability, credential leak, or authorization/authentication bug.
- A dependency bump whose changelog lists a CVE fix.

## Upgrade notes

- A required config or environment variable change.
- A dependency version floor raise (minimum supported runtime/toolchain).
- Any manual step a user must take that isn't automatic.

## Examples

- Breaking: "`--output` was removed; use `--out` instead (#123, abc1234)."
- Security: "Fixed an authorization check that let a non-admin user delete
  other users' data (#140, def5678)."
- Upgrade notes: "Requires Node >= 20 as of this release (#131, 9876abc)."
