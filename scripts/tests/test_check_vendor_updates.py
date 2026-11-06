import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import check_vendor_updates


VALID_COMMIT = "a" * 40
PINNED_TREE = "b" * 40
CURRENT_TREE = "c" * 40


class VendorUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.vendor_root = Path(self.temp_dir.name) / "vendor"

    def write_upstream(self, name="example", text=None):
        path = self.vendor_root / name / "UPSTREAM"
        path.parent.mkdir(parents=True)
        path.write_text(
            text
            or (
                "repo=owner/repository\n"
                "path=skills/example\n"
                f"commit={VALID_COMMIT}\n"
                "date=2026-11-06T00:00:00Z\n"
            ),
            encoding="utf-8",
        )
        return path

    def test_parse_upstream_accepts_literal_fields(self):
        upstream = check_vendor_updates.parse_upstream(self.write_upstream())

        self.assertEqual(upstream.repo, "owner/repository")
        self.assertEqual(upstream.path, "skills/example")
        self.assertEqual(upstream.commit, VALID_COMMIT)
        self.assertEqual(upstream.date, "2026-11-06T00:00:00Z")

    def test_parse_upstream_rejects_duplicate_or_unknown_fields(self):
        cases = {
            "duplicate": (
                "repo=owner/repository\nrepo=other/repository\n"
                f"path=skills/example\ncommit={VALID_COMMIT}\n"
                "date=2026-11-06T00:00:00Z\n"
            ),
            "unknown": (
                "repo=owner/repository\npath=skills/example\n"
                f"commit={VALID_COMMIT}\ndate=2026-11-06T00:00:00Z\n"
                "branch=main\n"
            ),
        }

        for label, text in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(check_vendor_updates.CheckerError):
                    check_vendor_updates.parse_upstream(
                        self.write_upstream(label, text)
                    )

    def test_parse_upstream_rejects_invalid_commit(self):
        path = self.write_upstream(
            text=(
                "repo=owner/repository\npath=skills/example\n"
                "commit=ABC123\ndate=2026-11-06T00:00:00Z\n"
            )
        )

        with self.assertRaises(check_vendor_updates.CheckerError):
            check_vendor_updates.parse_upstream(path)

    def test_equal_subtree_sha_is_unchanged_even_when_default_branch_advanced(self):
        self.write_upstream()

        def fetch(url, token):
            self.assertEqual(token, "token")
            if url == "https://api.github.com/repos/owner/repository":
                return {"default_branch": "main"}
            return {"sha": PINNED_TREE}

        result = check_vendor_updates.check_vendor(
            "example", self.vendor_root, "token", fetch=fetch
        )

        self.assertEqual(result.default_branch, "main")
        self.assertEqual(result.pinned_sha, PINNED_TREE)
        self.assertEqual(result.current_sha, PINNED_TREE)

    def test_different_subtree_sha_is_stale(self):
        self.write_upstream()

        def fetch(url, token):
            if url == "https://api.github.com/repos/owner/repository":
                return {"default_branch": "main"}
            if f"ref={VALID_COMMIT}" in url:
                return {"sha": PINNED_TREE}
            if "ref=main" in url:
                return {"sha": CURRENT_TREE}
            self.fail(f"unexpected URL: {url}")

        result = check_vendor_updates.check_vendor(
            "example", self.vendor_root, "token", fetch=fetch
        )

        self.assertEqual(result.pinned_sha, PINNED_TREE)
        self.assertEqual(result.current_sha, CURRENT_TREE)

    def test_missing_path_or_api_error_fails_closed(self):
        self.write_upstream()

        for response in ({"message": "Not Found"}, check_vendor_updates.CheckerError("rate limited")):
            with self.subTest(response=response):
                def fetch(url, token):
                    if url == "https://api.github.com/repos/owner/repository":
                        return {"default_branch": "main"}
                    if isinstance(response, Exception):
                        raise response
                    return response

                with self.assertRaises(check_vendor_updates.CheckerError):
                    check_vendor_updates.check_vendor(
                        "example", self.vendor_root, "token", fetch=fetch
                    )

    def test_github_json_wraps_invalid_utf8_as_checker_error(self):
        response = io.BytesIO(b"\xff")

        with mock.patch.object(
            check_vendor_updates.request, "urlopen", return_value=response
        ):
            with self.assertRaises(check_vendor_updates.CheckerError):
                check_vendor_updates.github_json(
                    "https://api.github.com/repos/owner/repository", "token"
                )

    def test_main_returns_one_and_names_stale_vendor(self):
        self.write_upstream("example")
        stale = check_vendor_updates.CheckResult(
            name="example",
            pinned_sha=PINNED_TREE,
            current_sha=CURRENT_TREE,
            default_branch="main",
        )
        stdout = io.StringIO()

        with mock.patch.object(check_vendor_updates, "check_vendor", return_value=stale):
            with mock.patch.dict("os.environ", {"GH_TOKEN": "token"}, clear=True):
                with contextlib.redirect_stdout(stdout):
                    status = check_vendor_updates.main(
                        ["--vendor-root", str(self.vendor_root)]
                    )

        self.assertEqual(status, 1)
        self.assertIn("example", stdout.getvalue())
        self.assertIn("STALE", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
