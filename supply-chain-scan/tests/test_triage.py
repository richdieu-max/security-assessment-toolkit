"""Unit tests for triage.py, run with: python -m unittest discover -s supply-chain-scan/tests"""
import csv
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import triage  # noqa: E402

EX = HERE.parent / "examples"


class TriageSamples(unittest.TestCase):
    def setUp(self):
        self.rows = triage.triage(EX / "gitleaks.sample.json", EX / "trivy.sample.json", EX / "dependabot.sample.json")

    def test_counts_and_lanes(self):
        self.assertEqual(len(self.rows), 7)
        self.assertEqual(sum(r["Lane"] == "Infrastructure" for r in self.rows), 4)
        self.assertEqual(sum(r["Lane"] == "Application" for r in self.rows), 3)

    def test_duplicate_across_tools_is_merged_with_highest_severity(self):
        dup = [r for r in self.rows if "CVE-2099-0002" in r["Finding"]]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["Source"], "trivy+dependabot")
        self.assertEqual(dup[0]["Severity"], "High")

    def test_dismissed_alerts_and_passed_checks_are_ignored(self):
        self.assertFalse(any("CVE-2099-0004" in r["Finding"] for r in self.rows))
        self.assertFalse(any("DS001" in r["Finding"] for r in self.rows))

    def test_sorted_by_severity_and_numbered(self):
        order = [triage.SEV_ORDER.index(r["Severity"]) for r in self.rows]
        self.assertEqual(order, sorted(order))
        self.assertEqual([r["ID"] for r in self.rows], [f"SC-{i:03d}" for i in range(1, 8)])

    def test_application_rows_are_routed_not_fixed(self):
        for r in self.rows:
            self.assertEqual(r["Status"], "Routed" if r["Lane"] == "Application" else "Open")


class Safety(unittest.TestCase):
    def test_secret_values_never_written(self):
        leak = [{"RuleID": "x", "File": "main.sh", "StartLine": 1, "Commit": "abc", "Secret": "super-secret-value"}]
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "g.json"
            p.write_text(json.dumps(leak))
            rows = triage.triage(gitleaks=str(p))
            triage.write(rows, d)
            text = (pathlib.Path(d) / "findings.csv").read_text()
            self.assertNotIn("super-secret-value", text)
            self.assertEqual(rows[0]["Lane"], "Infrastructure")

    def test_no_inputs_gives_empty_but_valid_output(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(triage.main(["--out", d]), 0)
            with (pathlib.Path(d) / "findings.csv").open() as fh:
                self.assertEqual(next(csv.reader(fh)), triage.COLUMNS)

    def test_fail_on_critical_infra(self):
        rep = {"Results": [{"Target": "img (ubuntu)", "Class": "os-pkgs", "Vulnerabilities": [
            {"VulnerabilityID": "CVE-2099-9999", "PkgName": "libz", "InstalledVersion": "1", "FixedVersion": "2", "Severity": "CRITICAL"}]}]}
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "t.json"
            p.write_text(json.dumps(rep))
            self.assertEqual(triage.main(["--trivy", str(p), "--out", d, "--fail-on-critical-infra"]), 1)


if __name__ == "__main__":
    unittest.main()
