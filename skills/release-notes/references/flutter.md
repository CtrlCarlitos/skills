# Repo type: flutter

## Detection

A `pubspec.yaml` file whose `dependencies` section declares the Flutter
SDK (a `flutter:` dependency with `sdk: flutter`), not just any Dart
package.

## Breaking

- A raised minimum SDK or deployment target: `environment.sdk` in
  `pubspec.yaml`, `minSdkVersion` in `android/app/build.gradle`, or
  `MinimumOSVersion`/the Xcode deployment target for iOS.
- A removed or changed-signature public widget, method, or exported
  class other packages or app code depend on.
- A renamed route name or changed navigation argument shape.

## Security

- A new or widened Android permission in `AndroidManifest.xml`
  (`<uses-permission>`).
- A new or changed iOS usage description in `Info.plist`
  (`NS*UsageDescription`) — required before the OS will prompt for that
  permission.
- A dependency bump in `pubspec.lock` whose changelog lists a CVE fix.

## Upgrade notes

- The `version:` field in `pubspec.yaml` (`x.y.z+build`) is the natural
  release boundary — use it as `<version>` in the heading when this repo
  is a single app/package.
- A raised Flutter/Dart SDK constraint in `pubspec.yaml`.
- Store-readiness notes are optional here: a changed app icon, display
  name, or store listing text worth calling out before a release.

## Examples

- Breaking: "Raised `minSdkVersion` to 23; the app no longer installs on
  Android 5 (#60, aa11bb2)."
- Security: "Added `CAMERA` permission for the new QR scanner feature
  (#63, cc22dd4)."
- Upgrade notes: "Raised the Dart SDK constraint to `>=3.4.0 <4.0.0` in
  `pubspec.yaml` (#65, ee33ff6)."
