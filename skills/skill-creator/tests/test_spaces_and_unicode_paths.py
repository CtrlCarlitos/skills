"""Regression tests: validation and packaging must work when the skill's
own path (not its `name:` field, which must stay kebab-case) contains
spaces and non-ASCII characters — e.g. a user's home directory like
"/Users/José García/My Projects/skill-creator".

Run from skills/skill-creator/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_skill import package_skill
from scripts.quick_validate import validate_skill

SKILL_MD = """---
name: my-test-skill
description: A skill used only to test packaging with odd paths.
---

Body content.
"""


def _write_skill(root: Path) -> Path:
    skill_dir = root / "My Projects — café" / "my-test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "notes résumé.md").write_text("notes", encoding="utf-8")
    return skill_dir


class SpacesAndUnicodePathTests(unittest.TestCase):
    def test_validate_skill_succeeds_with_spaces_and_unicode_in_path(self):
        with tempfile.TemporaryDirectory() as root:
            skill_dir = _write_skill(Path(root))

            valid, message = validate_skill(skill_dir)

            self.assertTrue(valid, message)

    def test_package_skill_succeeds_and_preserves_unicode_filenames(self):
        with tempfile.TemporaryDirectory() as root:
            skill_dir = _write_skill(Path(root))
            output_dir = Path(root) / "dist output"

            result = package_skill(str(skill_dir), str(output_dir))

            self.assertIsNotNone(result)
            self.assertTrue(result.is_file())
            with zipfile.ZipFile(result) as zf:
                names = zf.namelist()
            self.assertTrue(
                any("notes résumé.md" in n for n in names),
                f"expected a unicode-named entry in {names}",
            )
            # Zip entries must use forward slashes regardless of host OS.
            self.assertTrue(all("\\" not in n for n in names), names)


if __name__ == "__main__":
    unittest.main()
