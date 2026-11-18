"""Merge secrets, vulnerability and dependency findings into one triaged list.

Inputs (all optional, any combination):
  --gitleaks    gitleaks JSON report (run with --redact)
  --trivy       trivy fs/image JSON report (vuln, misconfig, secret scanners)
  --dependabot  GitHub Dependabot alerts JSON (gh api repos/<owner>/<repo>/dependabot/alerts)

Output:
  findings.csv  one row per finding, duplicates across tools merged
  summary.md    counts by lane and severity

Each finding is put in a LANE:
  Infrastructure : base image and OS packages, Dockerfile / IaC misconfiguration,
                   CI workflow actions, secrets in infra files. Fixed by the platform side.
  Application    : application dependencies and secrets in application code.
                   Written down and ROUTED to the application team, not fixed quietly.

Secret values are never written, even if a report contains them.
"""
import argparse
import csv
import json
import pathlib
import re
import sys

SEV_ORDER = ["Critical", "High", "Medium", "Low"]
SEV_MAP = {"critical": "Critical", "high": "High", "medium": "Medium", "moderate": "Medium", "low": "Low", "unknown": "Low", "negligible": "Low"}
INFRA_FILE = re.compile(r"(\.bicep|\.tf|\.ps1|\.psm1|\.sh|Dockerfile|docker-compose\.ya?ml|\.github/|\.env|\.service|\.conf)", re.I)
INFRA_ECOSYSTEMS = {"github_actions", "docker", "terraform"}
OWNER = {"Infrastructure": "Platform lead", "Application": "Application team"}
COLUMNS = ["ID", "Source", "Severity", "Lane", "Owner (role)", "Item", "Finding", "Fixed in", "Status", "Evidence"]


def sev(s):
    return SEV_MAP.get(str(s or "").lower(), "Low")


def lane_for_file(path):
    return "Infrastructure" if INFRA_FILE.search(path or "") else "Application"


def from_gitleaks(data, evidence):
    for leak in data or []:
        path = leak.get("File", "")
        yield {
            "key": ("secret", path, str(leak.get("StartLine")), leak.get("RuleID")),
            "Source": "gitleaks", "Severity": "High", "Lane": lane_for_file(path),
            "Item": f"{path}:{leak.get('StartLine')}",
            "Finding": f"Secret ({leak.get('RuleID')}) in commit {str(leak.get('Commit', ''))[:7]}. Rotate it, then remove it from history.",
            "Fixed in": "", "Evidence": evidence,
        }


def from_trivy(data, evidence):
    for res in (data or {}).get("Results", []) or []:
        target, klass = res.get("Target", ""), res.get("Class", "")
        for v in res.get("Vulnerabilities", []) or []:
            lane = "Infrastructure" if klass == "os-pkgs" else "Application"
            yield {
                "key": ("vuln", v.get("VulnerabilityID"), str(v.get("PkgName", "")).lower()),
                "Source": "trivy", "Severity": sev(v.get("Severity")), "Lane": lane,
                "Item": f"{v.get('PkgName')} {v.get('InstalledVersion')} ({target})",
                "Finding": f"{v.get('VulnerabilityID')}: {v.get('Title', '')}".strip(": "),
                "Fixed in": v.get("FixedVersion", "") or "no fix yet", "Evidence": evidence,
            }
        for m in res.get("Misconfigurations", []) or []:
            if m.get("Status", "FAIL") != "FAIL":
                continue
            yield {
                "key": ("misconfig", target, m.get("ID")),
                "Source": "trivy", "Severity": sev(m.get("Severity")), "Lane": "Infrastructure",
                "Item": target, "Finding": f"{m.get('ID')}: {m.get('Title', '')}", "Fixed in": "", "Evidence": evidence,
            }
        for s in res.get("Secrets", []) or []:
            yield {
                "key": ("secret", target, str(s.get("StartLine")), s.get("RuleID")),
                "Source": "trivy", "Severity": "High", "Lane": lane_for_file(target),
                "Item": f"{target}:{s.get('StartLine')}", "Finding": f"Secret ({s.get('RuleID')}). Rotate it, then remove it.",
                "Fixed in": "", "Evidence": evidence,
            }


def from_dependabot(data, evidence):
    for a in data or []:
        if a.get("state") != "open":
            continue
        dep = a.get("dependency", {}) or {}
        pkg = (dep.get("package") or {})
        adv = a.get("security_advisory", {}) or {}
        vid = adv.get("cve_id") or adv.get("ghsa_id")
        eco = str(pkg.get("ecosystem", "")).lower()
        patched = ((a.get("security_vulnerability") or {}).get("first_patched_version") or {}).get("identifier", "")
        yield {
            "key": ("vuln", vid, str(pkg.get("name", "")).lower()),
            "Source": "dependabot", "Severity": sev(adv.get("severity")),
            "Lane": "Infrastructure" if eco in INFRA_ECOSYSTEMS else "Application",
            "Item": f"{pkg.get('name')} ({dep.get('manifest_path', '')})",
            "Finding": f"{vid}: {adv.get('summary', '')}".strip(": "),
            "Fixed in": patched or "no fix yet", "Evidence": evidence,
        }


def merge(findings):
    """Same vulnerability in the same package from two tools becomes one row with both sources."""
    out = {}
    for f in findings:
        k = f.pop("key")
        if k in out:
            cur = out[k]
            if f["Source"] not in cur["Source"].split("+"):
                cur["Source"] += "+" + f["Source"]
            if f["Evidence"] not in cur["Evidence"].split("; "):
                cur["Evidence"] += "; " + f["Evidence"]
            if SEV_ORDER.index(f["Severity"]) < SEV_ORDER.index(cur["Severity"]):
                cur["Severity"] = f["Severity"]
            if not cur["Fixed in"] or cur["Fixed in"] == "no fix yet":
                cur["Fixed in"] = f["Fixed in"]
        else:
            out[k] = f
    rows = sorted(out.values(), key=lambda r: (SEV_ORDER.index(r["Severity"]), r["Lane"], r["Item"]))
    for i, r in enumerate(rows, 1):
        r["ID"] = f"SC-{i:03d}"
        r["Owner (role)"] = OWNER[r["Lane"]]
        r["Status"] = "Open" if r["Lane"] == "Infrastructure" else "Routed"
    return rows


def load(path):
    if not path:
        return None
    p = pathlib.Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() and p.stat().st_size else None


def triage(gitleaks=None, trivy=None, dependabot=None):
    found = []
    found += list(from_gitleaks(load(gitleaks), pathlib.Path(gitleaks).name if gitleaks else ""))
    found += list(from_trivy(load(trivy), pathlib.Path(trivy).name if trivy else ""))
    found += list(from_dependabot(load(dependabot), pathlib.Path(dependabot).name if dependabot else ""))
    return merge(found)


def write(rows, out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "findings.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    lines = ["# Supply-chain scan summary", "", "| Lane | " + " | ".join(SEV_ORDER) + " | Total |", "|---|" + "---|" * (len(SEV_ORDER) + 1)]
    for lane in ("Infrastructure", "Application"):
        counts = [sum(1 for r in rows if r["Lane"] == lane and r["Severity"] == s) for s in SEV_ORDER]
        lines.append(f"| {lane} | " + " | ".join(map(str, counts)) + f" | {sum(counts)} |")
    lines += ["", "Infrastructure rows are fixed on the platform side. Application rows are routed to the application team with the evidence, not fixed here."]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gitleaks")
    ap.add_argument("--trivy")
    ap.add_argument("--dependabot")
    ap.add_argument("--out", default=".")
    ap.add_argument("--fail-on-critical-infra", action="store_true", help="exit 1 if any Critical infrastructure finding is open")
    a = ap.parse_args(argv)
    rows = triage(a.gitleaks, a.trivy, a.dependabot)
    write(rows, a.out)
    infra = sum(1 for r in rows if r["Lane"] == "Infrastructure")
    print(f"{len(rows)} findings ({infra} infrastructure, {len(rows) - infra} application) -> {a.out}")
    if a.fail_on_critical_infra and any(r["Severity"] == "Critical" and r["Lane"] == "Infrastructure" for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
