"""Tests for the cross-platform artifact opener.

Run from skills/show-me/: python3 -m unittest discover -s tests
"""
import io
import tempfile
import unittest
from pathlib import Path

from scripts.open_artifact import detect_environment, main, opener_command, try_open


class DetectEnvironmentTests(unittest.TestCase):
    def test_windows_is_detected_from_system_name_alone(self):
        env = detect_environment(system="Windows", environ={}, proc_version="")
        self.assertEqual(env, "windows")

    def test_macos_desktop_by_default(self):
        env = detect_environment(system="Darwin", environ={}, proc_version="")
        self.assertEqual(env, "macos")

    def test_macos_over_ssh_is_headless(self):
        env = detect_environment(
            system="Darwin", environ={"SSH_CONNECTION": "1.2.3.4 1 5.6.7.8 22"}, proc_version=""
        )
        self.assertEqual(env, "macos-headless")

    def test_linux_with_wsl_distro_env_var_is_wsl(self):
        env = detect_environment(
            system="Linux", environ={"WSL_DISTRO_NAME": "Ubuntu"}, proc_version=""
        )
        self.assertEqual(env, "wsl")

    def test_linux_with_microsoft_in_proc_version_is_wsl(self):
        env = detect_environment(
            system="Linux",
            environ={},
            proc_version="Linux version 5.15.0 (Microsoft@Microsoft.com)",
        )
        self.assertEqual(env, "wsl")

    def test_linux_in_devcontainer_takes_priority_over_display(self):
        env = detect_environment(
            system="Linux",
            environ={"REMOTE_CONTAINERS": "true", "DISPLAY": ":0"},
            proc_version="",
        )
        self.assertEqual(env, "devcontainer")

    def test_linux_with_display_is_desktop(self):
        env = detect_environment(system="Linux", environ={"DISPLAY": ":0"}, proc_version="")
        self.assertEqual(env, "linux-desktop")

    def test_linux_with_no_display_and_no_wsl_signal_is_headless(self):
        env = detect_environment(system="Linux", environ={}, proc_version="")
        self.assertEqual(env, "linux-headless")


class OpenerCommandTests(unittest.TestCase):
    PATH = Path("/tmp/show-me-example.html")

    def test_windows_uses_cmd_start(self):
        cmd = opener_command("windows", self.PATH, which=lambda _: None)
        self.assertEqual(cmd, ["cmd.exe", "/c", "start", "", str(self.PATH)])

    def test_macos_uses_open(self):
        cmd = opener_command("macos", self.PATH, which=lambda _: None)
        self.assertEqual(cmd, ["open", str(self.PATH)])

    def test_wsl_uses_wslview_when_available(self):
        cmd = opener_command("wsl", self.PATH, which=lambda name: "/usr/bin/wslview" if name == "wslview" else None)
        self.assertEqual(cmd, ["wslview", str(self.PATH)])

    def test_wsl_has_no_opener_when_wslview_missing(self):
        cmd = opener_command("wsl", self.PATH, which=lambda _: None)
        self.assertIsNone(cmd)

    def test_linux_desktop_uses_xdg_open_when_available(self):
        cmd = opener_command(
            "linux-desktop", self.PATH, which=lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None
        )
        self.assertEqual(cmd, ["xdg-open", str(self.PATH)])

    def test_linux_desktop_has_no_opener_when_xdg_open_missing(self):
        cmd = opener_command("linux-desktop", self.PATH, which=lambda _: None)
        self.assertIsNone(cmd)

    def test_linux_headless_has_no_opener(self):
        cmd = opener_command("linux-headless", self.PATH, which=lambda _: "/would/be/found")
        self.assertIsNone(cmd)

    def test_macos_headless_has_no_opener(self):
        cmd = opener_command("macos-headless", self.PATH, which=lambda _: "/would/be/found")
        self.assertIsNone(cmd)

    def test_devcontainer_has_no_opener(self):
        cmd = opener_command("devcontainer", self.PATH, which=lambda _: "/would/be/found")
        self.assertIsNone(cmd)


class TryOpenTests(unittest.TestCase):
    def test_returns_true_and_never_waits_when_launch_succeeds(self):
        calls = []

        def fake_popen(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return object()  # try_open must not call .wait() on this

        result = try_open(["open", "/tmp/x.html"], popen=fake_popen)

        self.assertTrue(result)
        self.assertEqual(calls[0][0], ["open", "/tmp/x.html"])

    def test_returns_false_without_raising_when_launch_fails(self):
        def failing_popen(cmd, **kwargs):
            raise OSError("command not found")

        result = try_open(["nonexistent"], popen=failing_popen)

        self.assertFalse(result)

    def test_real_nonexistent_command_does_not_raise(self):
        """No mocking: a command that genuinely doesn't exist on this
        machine must still return False, not raise."""
        result = try_open(["definitely-not-a-real-command-xyz-show-me"])

        self.assertFalse(result)


class MainTests(unittest.TestCase):
    def _run(self, argv, **overrides):
        stdout, stderr = io.StringIO(), io.StringIO()
        kwargs = dict(
            system="Linux",
            environ={"DISPLAY": ":0"},
            proc_version="",
            which=lambda _: None,
            popen=lambda *a, **k: object(),
            stdout=stdout,
            stderr=stderr,
        )
        kwargs.update(overrides)
        exit_code = main(argv, **kwargs)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_missing_artifact_reports_error_and_exits_nonzero(self):
        exit_code, _, stderr = self._run(["/no/such/path/show-me-example.html"])

        self.assertEqual(exit_code, 1)
        self.assertIn("not found", stderr)

    def test_existing_artifact_with_available_opener_reports_success(self):
        with tempfile.NamedTemporaryFile(suffix=".html") as f:
            resolved = str(Path(f.name).resolve())
            exit_code, stdout, _ = self._run(
                [f.name],
                which=lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None,
            )

        self.assertEqual(exit_code, 0)
        # main() resolves the path (Path.resolve()), which can rewrite it --
        # e.g. Windows expands a short 8.3 alias like RUNNER~1 to the real
        # long username. Compare against the same resolution, not the raw
        # input string.
        self.assertIn(resolved, stdout)
        self.assertIn("Opened with", stdout)

    def test_existing_artifact_with_no_opener_still_reports_the_path(self):
        with tempfile.NamedTemporaryFile(suffix=".html") as f:
            resolved = str(Path(f.name).resolve())
            exit_code, stdout, _ = self._run([f.name], environ={})  # no DISPLAY -> headless

        self.assertEqual(exit_code, 0)
        self.assertIn(resolved, stdout)
        self.assertIn("No opener available", stdout)


if __name__ == "__main__":
    unittest.main()
