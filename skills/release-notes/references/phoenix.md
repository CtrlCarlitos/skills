# Repo type: phoenix

## Detection

A `mix.exs` file whose dependency list includes `:phoenix`.

## Breaking

- A changed or removed route in `router.scope`/`router.pipeline`.
- A renamed or removed LiveView event (`handle_event("name", ...)`) or
  `push_event`/`handle_info` message a client or JS hook depends on.
- A changed context function's public API (arity, argument order, or
  return shape) used outside the app (e.g. from an umbrella sibling).
- An Elixir or OTP minimum version bump in `mix.exs` (`elixir: "~> ..."`).

## Security

- Changed `Plug` pipelines that affect authentication/authorization
  (`pipeline :authenticated`, `plug :require_authenticated_user`, etc.).
- Changed CSRF/session config in `endpoint.ex` or `config/*.exs`.
- A dependency bump in `mix.lock` whose changelog lists a CVE fix.

## Upgrade notes

- A new file under `priv/repo/migrations/` means the operator must run
  `mix ecto.migrate` (or the release's migration task) before/with
  deploying.
- A new or renamed environment variable read in `config/runtime.exs` —
  deploys will fail or silently misconfigure without it.
- An Elixir/OTP/Phoenix version floor raise in `mix.exs`.

## Examples

- Breaking: "Renamed the `\"save\"` LiveView event to `\"save_form\"` in
  `UserLive.Edit`; update any custom JS hooks (#44, 7bb21aa)."
- Security: "Added `plug :require_authenticated_user` to the `:admin`
  scope, which was previously reachable unauthenticated (#50, c1d9e02)."
- Upgrade notes: "Added migration `20260115_add_users_role`; run
  `mix ecto.migrate` before starting the new release (#52, 9fa3bcd)."
