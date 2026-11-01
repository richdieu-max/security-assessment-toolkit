"""Sanity-check a built workbook: sheet order, the formulas that drive scoring,
the data validation lists, and that no formula cell was overwritten with text.

    python tools/check_workbook.py templates/security-assessment-template.xlsx examples/contoso-clinic-assessment.xlsx

Exits non-zero on the first failure so CI goes red.
"""
import sys

from openpyxl import load_workbook

EXPECTED_SHEETS = [
    "Read Me", "Summary", "Rating Matrix", "Threat Model", "Risk Register",
    "Control Register", "Compliance Mapping", "Config Evidence", "Logging Validation",
]


def check(path):
    wb = load_workbook(path)
    assert wb.sheetnames == EXPECTED_SHEETS, f"{path}: sheets {wb.sheetnames}"

    rr = wb["Risk Register"]
    header = [c.value for c in rr[4]][:14]
    assert header[6:8] == ["Score", "Severity"], f"{path}: Risk Register header {header}"
    for row in rr.iter_rows(min_row=5, max_row=rr.max_row):
        rid, score, sev = row[0].value, row[6].value, row[7].value
        if rid is None:
            continue
        assert str(score).startswith("=IF("), f"{path}: {rid} Score is not a formula: {score!r}"
        assert "'Rating Matrix'!$B$16" in str(sev), f"{path}: {rid} Severity does not read the rating bands: {sev!r}"

    validations = " ".join(dv.formula1 or "" for dv in rr.data_validations.dataValidation)
    assert '"Critical"' in validations, f"{path}: Override column is missing its Critical-only list"
    assert "Open,Mitigating" in validations, f"{path}: Status column is missing its list"

    summary = wb["Summary"]
    assert str(summary["B5"].value).startswith("=COUNTIF("), f"{path}: Summary B5 is not a COUNTIF"
    assert str(summary["B12"].value).startswith("=COUNTIF("), f"{path}: Summary B12 is not a COUNTIF"

    matrix = wb["Rating Matrix"]
    assert matrix["B16"].value == 9 and matrix["B19"].value == 1, f"{path}: severity bands moved"
    print(f"ok  {path}: {len(wb.sheetnames)} sheets, scoring formulas and validation lists present")


if __name__ == "__main__":
    paths = sys.argv[1:] or ["templates/security-assessment-template.xlsx", "examples/contoso-clinic-assessment.xlsx"]
    for p in paths:
        check(p)
