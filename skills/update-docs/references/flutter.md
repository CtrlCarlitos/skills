# Repo type: flutter

## Where docs live

`README.md` at the package/app root. `dart doc` comments (`///`) above
public classes, widgets, and members -- rendered to `doc/api/` (`dart
doc`'s default output, not usually committed).

## What's generated, and by what

`doc/api/` is `dart doc`'s generated output -- never hand-edit it; edit
the `///` comments and regenerate. If `pubspec.yaml`'s `version` field
disagrees with what a doc states as the current version, the doc is
stale, not the manifest.

## What's public (must be documented)

Any exported (non-underscore-prefixed) class, widget, or member in a
package meant for reuse. For an app (not a package), the public surface
is thinner: routes/navigation, and whatever the README promises
(supported platforms, required permissions, build flavors).

## "Don't document" markers

An identifier prefixed with `_` (Dart's privacy convention) is never
part of the public API, regardless of doc comments on it.

## Breaking vs. routine for docs purposes

A raised `minSdkVersion`/iOS deployment target, a removed/changed public
widget or method, or a new required permission (`AndroidManifest.xml`'s
`<uses-permission>`, iOS `Info.plist`'s `NS*UsageDescription`) is
breaking or security-relevant respectively -- not just a routine update.
