import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent

class AuditGroundingCliTests(unittest.TestCase):
    def test_reports_a_gap_for_an_uncovered_curricular_topic(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit_grounding", workspace, "lenguaje", "sustantivos", "4"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertIn("gap", result.stdout.lower())

    def test_reports_a_general_topic_with_no_gap(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit_grounding", workspace, "youtube", "channel-setup", "n/a", "--general"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertNotIn("gap", result.stdout.lower())
