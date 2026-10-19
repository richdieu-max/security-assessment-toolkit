"""Build the security assessment workbook.

    python tools/build_workbook.py            -> templates/security-assessment-template.xlsx (blank, one example row per sheet)
    python tools/build_workbook.py --example  -> examples/contoso-clinic-assessment.xlsx    (fully worked fictional example)

Also writes one CSV per data sheet next to the workbook so changes diff cleanly in git.
The example organisation, system and findings are invented.
"""
import csv
import os
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

EXAMPLE = "--example" in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "examples" if EXAMPLE else "templates")
OUT_NAME = "contoso-clinic-assessment.xlsx" if EXAMPLE else "security-assessment-template.xlsx"

FONT = "Arial"
INK = "1F2328"
ACCENT = "B42318"  # dark red accent bar
HEAD_FILL = PatternFill("solid", fgColor="24292F")
INPUT_FILL = PatternFill("solid", fgColor="FFF8C5")
EXAMPLE_FONT = Font(name=FONT, size=10, italic=True, color="0000FF")
BODY = Font(name=FONT, size=10, color=INK)
BODY_BLUE = Font(name=FONT, size=10, color="0000FF")
HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
TITLE = Font(name=FONT, size=14, bold=True, color=INK)
SUB = Font(name=FONT, size=10, italic=True, color="57606A")
THIN = Side(style="thin", color="D0D7DE")
GRID = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
SEV_FILLS = {"Critical": "7A1F1F", "High": "D1242F", "Medium": "E3A008", "Low": "2DA44E"}

wb = Workbook()
csv_sheets = []


def title_block(ws, title, subtitle):
    ws["A1"] = title
    ws["A1"].font = TITLE
    ws["A2"] = subtitle
    ws["A2"].font = SUB
    ws.row_dimensions[1].height = 22
    ws.sheet_view.showGridLines = False


def table(ws, start_row, headers, rows, widths, example_rows=0, input_cols=None):
    """Write a header and rows. The first `example_rows` rows are styled as examples.
    input_cols: 1-based columns a user is expected to fill in (shaded when blank-template)."""
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=c, value=h)
        cell.font, cell.fill, cell.border = HEAD, HEAD_FILL, GRID
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for r, row in enumerate(rows, start_row + 1):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border, cell.alignment = GRID, WRAP
            is_formula = isinstance(v, str) and v.startswith("=")
            if r - start_row <= example_rows and not EXAMPLE:
                cell.font = EXAMPLE_FONT if not is_formula else BODY
            else:
                cell.font = BODY if is_formula else BODY_BLUE
    if not EXAMPLE and input_cols:
        for r in range(start_row + 1 + example_rows, start_row + 1 + len(rows)):
            for c in input_cols:
                ws.cell(row=r, column=c).fill = INPUT_FILL
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    return start_row + len(rows)


def blank_rows(n, width, template_row=None):
    """Blank rows for a template; template_row(i) can supply formulas per row."""
    return [template_row(i) if template_row else [None] * width for i in range(n)]


def remember_csv(ws, header_row, last_row, name):
    csv_sheets.append((ws, header_row, last_row, name))


# ---------------------------------------------------------------- Read Me
ws = wb.active
ws.title = "Read Me"
title_block(ws, "Security assessment workbook",
            "Contoso Clinic (fictional example)" if EXAMPLE else "Template · replace the example rows with your own")
readme = [
    ("Purpose", "One workbook for a cloud security assessment: rating matrix, threat model, risk register, compliance mapping, control register, configuration evidence and logging validation."),
    ("Order of work", "1 Rating Matrix (agree the scales first) · 2 Threat Model · 3 Risk Register · 4 Control Register · 5 Compliance Mapping · 6 Config Evidence · 7 Logging Validation · 8 Summary updates itself."),
    ("Colour legend", "Blue text = values you type. Black text = formulas, do not overwrite. Yellow fill = cells waiting for input. Blue italic = example row: replace it."),
    ("Scoring", "Likelihood (1-3) x Impact (1-3) = Score (1-9). Severity comes from the bands on the Rating Matrix sheet, so changing a band there re-rates every risk."),
    ("Evidence rule", "Every statement that something is built or working cites an evidence file in the Evidence column. No evidence, no Met or Built status."),
    ("Owners", "Owners are roles (Platform lead, Client security owner), never personal names, so the workbook stays valid when people change."),
    ("Scope note", "The system, organisation and findings in the example are invented." if EXAMPLE else "Record the scope and the out-of-scope items here before the first finding."),
]
r = 4
for k, v in readme:
    ws.cell(row=r, column=1, value=k).font = Font(name=FONT, size=10, bold=True, color=INK)
    c = ws.cell(row=r, column=2, value=v)
    c.font, c.alignment = BODY, WRAP
    r += 1
ws.column_dimensions["A"].width = 18
ws.column_dimensions["B"].width = 110

# ---------------------------------------------------------------- Rating Matrix
ws = wb.create_sheet("Rating Matrix")
title_block(ws, "Risk rating matrix", "Scales, severity bands and the heat map. The bands drive every Severity formula in the workbook.")
table(ws, 4, ["Score", "Likelihood", "Meaning"], [
    [3, "Likely", "Expected within the engagement or the first quarter of operation with no further mistakes."],
    [2, "Possible", "Needs a plausible sequence of events or a single mistake."],
    [1, "Unlikely", "Needs a privileged insider, a chained failure or a change to the design."],
], [10, 14, 70])
table(ws, 9, ["Score", "Impact", "Meaning"], [
    [3, "Severe", "Regulated or personal data exposed or altered; loss of the primary data store or its backups."],
    [2, "Moderate", "Reduced monitoring or defence in depth; a control weakened while a second one still holds."],
    [1, "Minor", "Operational or documentation gap; no data exposure; fixable in normal operations."],
], [10, 14, 70])
ws.cell(row=14, column=1, value="Severity bands").font = Font(name=FONT, size=11, bold=True, color=INK)
table(ws, 15, ["Severity", "Minimum score", "Required response", "Reported within"], [
    ["Critical", 9, "Reported to the system owner within one business day; fix or written risk acceptance before sign-off.", "1 business day"],
    ["High", 6, "Agreed plan (fix, mitigate or accept) before sign-off.", "Next status update"],
    ["Medium", 3, "Recommended action and target date; may be accepted in writing.", "Findings report"],
    ["Low", 1, "Handled in normal operations.", "Findings report"],
], [10, 14, 70, 20])
ws.cell(row=20, column=1, value="Any confirmed data exposure is Critical at any score (Override column on the Risk Register).").font = SUB
ws.cell(row=22, column=1, value="Heat map").font = Font(name=FONT, size=11, bold=True, color=INK)
heads = ["", "Impact 3", "Impact 2", "Impact 1"]
for c, h in enumerate(heads, 1):
    cell = ws.cell(row=23, column=c, value=h)
    cell.font, cell.fill, cell.border = HEAD, HEAD_FILL, GRID
for i, lk in enumerate([3, 2, 1]):
    rr = 24 + i
    cell = ws.cell(row=rr, column=1, value=f"Likelihood {lk}")
    cell.font, cell.border = Font(name=FONT, size=10, bold=True, color=INK), GRID
    for j, im in enumerate([3, 2, 1]):
        cell = ws.cell(row=rr, column=2 + j, value=f"={lk}*{im}")
        cell.font, cell.border = Font(name=FONT, size=11, bold=True, color="FFFFFF"), GRID
        cell.alignment = Alignment(horizontal="center", vertical="center")
for sev, rule in [("Critical", "B24>=$B$16"), ("High", "B24>=$B$17"), ("Medium", "B24>=$B$18"), ("Low", "B24>=$B$19")]:
    ws.conditional_formatting.add("B24:D26", FormulaRule(formula=[rule], fill=PatternFill("solid", fgColor=SEV_FILLS[sev]), stopIfTrue=True))
# Named thresholds used by the Risk Register
BAND_CRIT, BAND_HIGH, BAND_MED = "'Rating Matrix'!$B$16", "'Rating Matrix'!$B$17", "'Rating Matrix'!$B$18"

# ---------------------------------------------------------------- Threat Model
ws = wb.create_sheet("Threat Model")
title_block(ws, "Threat model", "Assets, trust boundaries and STRIDE at each boundary. Unmitigated threats become rows on the Risk Register.")
assets = [
    ["A1", "Patient appointment records", "Azure SQL Database, private endpoint only", "Personal and health-adjacent data; the product", "EV-03"],
    ["A2", "Application secrets", "Key Vault, RBAC, private endpoint", "A leaked signing key forges sessions", "EV-04"],
    ["A3", "Database backups", "Recovery Services vault, geo-redundant", "Recovery after corruption or ransomware", "EV-07"],
    ["A4", "Audit and platform logs", "Log Analytics workspace, archive storage", "Evidence for every other control", "EV-08"],
    ["A5", "Administrator identities", "Entra ID with Conditional Access", "Control of everything above", "EV-01"],
] if EXAMPLE else [["A1", "Customer records (example)", "Where it lives", "Why it matters", "EV-01"]] + blank_rows(9, 5)
end = table(ws, 4, ["ID", "Asset", "Where it lives", "Why it matters", "Evidence"], assets, [8, 30, 36, 40, 12],
            example_rows=0 if EXAMPLE else 1, input_cols=[1, 2, 3, 4, 5])
remember_csv(ws, 4, end, "threat-model-assets")

b0 = end + 3
ws.cell(row=b0 - 1, column=1, value="Trust boundaries").font = Font(name=FONT, size=11, bold=True, color=INK)
bounds = [
    ["B1", "Internet to application gateway", "HTTPS 443 through WAF (prevention mode)", "Built", "EV-02"],
    ["B2", "Gateway to app service", "Private integration; app accepts gateway traffic only", "Built", "EV-02"],
    ["B3", "App to database", "Private endpoint; Entra-only authentication", "Built", "EV-03"],
    ["B4", "App identity to Key Vault", "Managed identity with Secrets User role only", "Built", "EV-04"],
    ["B5", "Administrators to control plane", "Entra ID, phishing-resistant MFA, Conditional Access", "Partial: two standing Owners", "EV-01"],
] if EXAMPLE else [["B1", "Internet to front door (example)", "Entry points crossing it", "Built / Partial / Planned", "EV-02"]] + blank_rows(7, 5)
end = table(ws, b0, ["ID", "Boundary", "Entry points crossing it", "Status", "Evidence"], bounds, [8, 30, 36, 40, 12],
            example_rows=0 if EXAMPLE else 1, input_cols=[1, 2, 3, 4, 5])
remember_csv(ws, b0, end, "threat-model-boundaries")

s0 = end + 3
ws.cell(row=s0 - 1, column=1, value="STRIDE at each boundary").font = Font(name=FONT, size=11, bold=True, color=INK)
stride = [
    ["B1", "S", "Forged client or replayed session", "TLS 1.2+, short-lived tokens, WAF bot rules", "None", "-"],
    ["B1", "T", "Malicious request bodies", "WAF OWASP managed rules in prevention mode", "Custom rules not yet tuned", "R-04"],
    ["B1", "D", "Request flood", "WAF rate limit on sign-in path", "No DDoS protection plan", "R-06"],
    ["B3", "I", "Database read outside the app", "Private endpoint; public access disabled", "None", "-"],
    ["B4", "E", "App identity used to write secrets", "Secrets User role only", "None", "-"],
    ["B5", "E", "Standing admin rights misused", "MFA and Conditional Access", "Two standing Owners, no just-in-time access", "R-01"],
    ["B5", "R", "Admin change with no trace", "Activity log exported to workspace", "Archive not immutable", "R-03"],
    ["A3", "T", "Backups deleted by a compromised admin", "Soft delete", "Vault immutability not enabled", "R-02"],
] if EXAMPLE else [["B1", "S", "Threat (example)", "Control in place", "Gap", "R-01"]] + blank_rows(11, 6)
end = table(ws, s0, ["Boundary / asset", "STRIDE", "Threat", "Control in place", "Gap", "Risk Register ref"], stride,
            [16, 8, 34, 40, 34, 14], example_rows=0 if EXAMPLE else 1, input_cols=[1, 2, 3, 4, 5, 6])
dv = DataValidation(type="list", formula1='"S,T,R,I,D,E,S/E,T/I"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"B{s0 + 1}:B{end}")
remember_csv(ws, s0, end, "threat-model-stride")
for col, w in zip("ABCDEF", [14, 32, 40, 42, 36, 14]):
    ws.column_dimensions[col].width = w

# ---------------------------------------------------------------- Risk Register
ws = wb.create_sheet("Risk Register")
title_block(ws, "Risk register", "Score and Severity are formulas. Type Likelihood, Impact and, only for confirmed data exposure, Override = Critical.")
H0 = 4


def risk_row(i, rid="", finding="", asset="", found="", lk=None, im=None, override="", status="", action="", refs="", due="", owner=""):
    r = H0 + 1 + i
    return [rid, finding, asset, found, lk, im,
            f'=IF(OR(E{r}="",F{r}=""),"",E{r}*F{r})',
            f'=IF(G{r}="","",IF(OR(I{r}="Critical",G{r}>={BAND_CRIT}),"Critical",IF(G{r}>={BAND_HIGH},"High",IF(G{r}>={BAND_MED},"Medium","Low"))))',
            override, status, action, refs, due, owner]


if EXAMPLE:
    risks = [
        ("R-01", "Two user accounts hold standing Owner; no just-in-time elevation.", "Entra ID / subscription", "Posture check", 2, 3, "", "Open", "License PIM, convert to eligible assignments, review monthly.", "AC-6(5); PR.AA-05; ISO 8.2", "Before go-live", "Client security owner"),
        ("R-02", "Backup vault immutability disabled: a compromised admin could delete backups.", "Recovery Services vault", "Posture check", 2, 3, "", "Mitigating", "Enable immutability (Unlocked), then lock after review.", "CP-9; PR.DS-11; ISO 8.13", "2 weeks", "Platform lead"),
        ("R-03", "Log archive has no time-based retention lock.", "Archive storage", "Logging review", 1, 3, "", "Open", "Apply time-based retention; client decides when to lock.", "AU-9; PR.PS-04; ISO 8.15", "After acceptance", "Client security owner"),
        ("R-04", "WAF custom rules not tuned; some legitimate requests blocked in test.", "Application gateway", "Functional test", 2, 2, "", "Open", "Tune exclusions from a week of logs; keep prevention mode.", "SC-7; PR.IR-01; ISO 8.20", "Before go-live", "Platform lead"),
        ("R-05", "Alert recipient is a single mailbox owned by the engagement.", "Action group", "Logging review", 2, 2, "", "Open", "Client supplies a monitored shared mailbox and on-call rota.", "IR-6; RS.MA-01; ISO 5.24", "Handover", "Client operations"),
        ("R-06", "No DDoS protection plan on the public entry point.", "Gateway public IP", "Threat model", 1, 2, "", "Accepted", "Accept for launch; revisit at 10x traffic.", "SC-5; PR.IR-01", "Review in 6 months", "Client security owner"),
        ("R-07", "Network flow logs not enabled.", "Virtual networks", "Posture check", 2, 1, "", "Open", "Enable VNet flow logs to the workspace.", "AU-12; DE.CM-01; ISO 8.16", "2 weeks", "Platform lead"),
        ("R-08", "Runbook lists a retired admin group.", "Documentation", "Document review", 1, 1, "", "Closed", "Runbook corrected in v1.1.", "CM-3", "Done", "Platform lead"),
    ]
    rows = [risk_row(i, *x) for i, x in enumerate(risks)]
    example_rows = 0
else:
    rows = [risk_row(0, "R-01", "Example: standing Owner on the subscription with no just-in-time access.", "Entra ID / subscription", "Posture check", 2, 3, "", "Open", "Convert to eligible assignments.", "AC-6(5); PR.AA-05", "Before go-live", "Security owner (role)")]
    rows += [risk_row(i) for i in range(1, 40)]
    example_rows = 1
end = table(ws, H0, ["ID", "Finding", "Asset / control", "Found in", "Likelihood (1-3)", "Impact (1-3)", "Score", "Severity",
                     "Override", "Status", "Action to close", "Framework refs", "Due", "Owner (role)"],
            rows, [8, 44, 22, 16, 11, 10, 8, 11, 11, 12, 40, 24, 16, 20], example_rows=example_rows,
            input_cols=[1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14])
RISK_LAST = end
for col in ("E", "F"):
    v = DataValidation(type="whole", operator="between", formula1="1", formula2="3", allow_blank=True, showErrorMessage=True, error="Enter 1, 2 or 3")
    ws.add_data_validation(v)
    v.add(f"{col}{H0 + 1}:{col}{end}")
v = DataValidation(type="list", formula1='"Critical"', allow_blank=True)
ws.add_data_validation(v)
v.add(f"I{H0 + 1}:I{end}")
v = DataValidation(type="list", formula1='"Open,Mitigating,Mitigated,Accepted,Closed"', allow_blank=True)
ws.add_data_validation(v)
v.add(f"J{H0 + 1}:J{end}")
for sev, color in SEV_FILLS.items():
    ws.conditional_formatting.add(f"H{H0 + 1}:H{end}", FormulaRule(formula=[f'$H{H0 + 1}="{sev}"'], fill=PatternFill("solid", fgColor=color), font=Font(name=FONT, color="FFFFFF", bold=True)))
remember_csv(ws, H0, end, "risk-register")

# ---------------------------------------------------------------- Control Register
ws = wb.create_sheet("Control Register")
title_block(ws, "Control register", "Every rule, policy, role and alert the build created, where it lives, why it exists and how it maps.")
ctrls = [
    ["GOV-01", "Governance", "Management group hierarchy (root > platform / workloads / sandbox)", "Tenant root", "Structure", "Set policy once; every subscription inherits it", "PL-8, CM-2", "GV.PO-01", "5.23, 8.9", "Built", "EV-01"],
    ["POL-01", "Policy", "Allowed locations (two paired regions)", "Root management group", "Deny", "Keeps data in approved regions", "CM-6, SA-9(5)", "PR.PS-01", "5.23", "Built", "EV-05"],
    ["POL-02", "Policy", "No public IP on network interfaces", "Root management group", "Deny", "Removes direct internet exposure of VMs", "SC-7", "PR.IR-01", "8.20", "Built", "EV-05"],
    ["IAM-01", "Identity", "Security Reader for the security team group", "Root management group", "RBAC", "Read-only visibility for monitoring", "AC-6", "PR.AA-05", "5.15, 8.2", "Built", "EV-01"],
    ["IAM-02", "Identity", "Just-in-time Owner through PIM", "Subscription", "PIM", "No standing admin rights", "AC-6(5), AC-2(7)", "PR.AA-05", "8.2", "Open (R-01)", "-"],
    ["NET-01", "Network", "Deny-by-default NSGs; app port from gateway subnet only", "Workload VNet", "NSG", "Limits east-west movement", "SC-7, AC-4", "PR.IR-01", "8.20, 8.22", "Built", "EV-02"],
    ["KV-01", "Secrets", "Key Vault: RBAC, purge protection, private endpoint", "Workload resource group", "Config", "Secrets reachable only from the app network", "SC-12, SC-28", "PR.DS-01", "8.24", "Built", "EV-04"],
    ["BAK-01", "Backup", "Geo-redundant vault, cross-region restore, soft delete", "Workload resource group", "Config", "Recover from region loss or deletion", "CP-9, CP-6", "PR.DS-11", "8.13", "Built", "EV-07"],
    ["BAK-02", "Backup", "Vault immutability", "Workload resource group", "Config", "Backups cannot be deleted early", "CP-9", "PR.DS-11", "8.13", "Open (R-02)", "-"],
    ["LOG-01", "Logging", "Activity log to workspace, 365-day retention", "Subscription", "Diagnostic setting", "Control-plane history beyond 90 days", "AU-2, AU-11, AU-12", "PR.PS-04", "8.15", "Built", "EV-08"],
    ["DEF-01", "Threat protection", "Defender for Cloud plans and security contact", "Subscription", "Config", "Threat alerts reach a person", "SI-4, IR-6", "DE.CM-01", "8.16", "Built", "EV-06"],
] if EXAMPLE else [["POL-01", "Policy", "Allowed locations (example)", "Root management group", "Deny", "Keeps data in approved regions", "CM-6", "PR.PS-01", "5.23", "Built", "EV-05"]] + blank_rows(39, 11)
end = table(ws, 4, ["ID", "Area", "Rule / control", "Where it lives", "Enforcement", "Why it exists", "NIST SP 800-53 R5", "NIST CSF 2.0", "ISO/IEC 27001:2022 Annex A", "Status", "Evidence"],
            ctrls, [9, 14, 42, 24, 14, 36, 18, 12, 16, 14, 10], example_rows=0 if EXAMPLE else 1, input_cols=list(range(1, 12)))
remember_csv(ws, 4, end, "control-register")

# ---------------------------------------------------------------- Compliance Mapping
ws = wb.create_sheet("Compliance Mapping")
title_block(ws, "Compliance mapping", "NIST CSF 2.0 to SP 800-53 and ISO/IEC 27001:2022. Met = in place and evidenced; Partial = in place with a recorded gap; Gap = not in place.")
maps = [
    ["Govern", "GV.RR roles and responsibilities", "PM-2, PL-2", "5.2", "Owners are roles; runbook and registers under version control", "Met", "Runbook"],
    ["Govern", "GV.PO policy", "PL-1, CM-1", "5.1", "Azure Policy baseline is the enforced policy; exemptions recorded", "Met", "EV-05"],
    ["Identify", "ID.AM asset management", "CM-8", "5.9", "Resource inventory captured per evidence run", "Met", "EV-01"],
    ["Identify", "ID.RA risk assessment", "RA-3, RA-5", "8.8", "This threat model and risk register; Defender recommendations", "Met", "Risk Register"],
    ["Protect", "PR.AA identity and access", "AC-2, AC-6, IA-2", "5.15, 5.18, 8.2, 8.5", "Group RBAC and MFA; standing Owners remain", "Partial", "R-01"],
    ["Protect", "PR.DS data security", "SC-8, SC-12, SC-28", "8.24", "TLS 1.2+, encryption at rest, keys in Key Vault", "Met", "EV-04"],
    ["Protect", "PR.DS-11 backups", "CP-9, CP-10", "8.13", "Geo-redundant backups; immutability not enabled", "Partial", "R-02"],
    ["Protect", "PR.PS platform security", "CM-2, CM-6, SI-2", "8.9, 8.19", "Policy guardrails; automatic patching", "Met", "EV-05"],
    ["Protect", "PR.IR infrastructure resilience", "SC-7, SC-5", "8.20, 8.22", "Segmented network; WAF; no DDoS plan (accepted)", "Partial", "R-06"],
    ["Detect", "DE.CM continuous monitoring", "SI-4, AU-6", "8.16", "Defender plans, alerts; no flow logs yet", "Partial", "R-07"],
    ["Respond", "RS.MA incident management", "IR-4, IR-6", "5.24, 5.26", "Alert routing exists; recipient to be handed over", "Partial", "R-05"],
    ["Recover", "RC.RP recovery plan execution", "CP-10", "5.30", "Restore tested once; schedule quarterly", "Met", "EV-07"],
] if EXAMPLE else [["Protect", "PR.AA identity and access (example)", "AC-2, AC-6", "5.15, 8.2", "How the control is met", "Partial", "R-01"]] + blank_rows(29, 7)
end = table(ws, 4, ["CSF 2.0 function", "CSF category", "SP 800-53 control(s)", "ISO/IEC 27001:2022 Annex A", "How it is met", "Status", "Evidence / risk"],
            maps, [14, 30, 18, 20, 52, 10, 16], example_rows=0 if EXAMPLE else 1, input_cols=list(range(1, 8)))
v = DataValidation(type="list", formula1='"Met,Partial,Gap,Not applicable"', allow_blank=True)
ws.add_data_validation(v)
v.add(f"F5:F{end}")
remember_csv(ws, 4, end, "compliance-mapping")

# ---------------------------------------------------------------- Config Evidence
ws = wb.create_sheet("Config Evidence")
title_block(ws, "Secure configuration evidence", "Evidence index. Each run folder carries a SHA-256 manifest so a reviewer can confirm nothing changed after capture.")
ev = [
    ["EV-01", "Identity and role assignments", "role-assignments.json", "posture-20261012T1400Z", "Captured", ""],
    ["EV-02", "NSG rules and effective rules per NIC", "nsg-rules.json, effective-rules.json", "posture-20261012T1400Z", "Captured", ""],
    ["EV-03", "Database network and authentication settings", "sql-config.json", "posture-20261012T1400Z", "Captured", ""],
    ["EV-04", "Key Vault configuration and role assignments", "keyvault.json", "posture-20261012T1400Z", "Captured", ""],
    ["EV-05", "Azure Policy compliance report", "policy-states.csv", "posture-20261012T1400Z", "Captured", "Guardrails 100% on in-scope resources"],
    ["EV-06", "Defender plans and security contact", "defender.json", "posture-20261012T1400Z", "Captured", ""],
    ["EV-07", "Backup vault settings and last restore test", "vault.json, restore-test.md", "posture-20261012T1400Z", "Captured", "Restore test 2026-10-10"],
    ["EV-08", "Diagnostic settings and retention", "diagnostics.json", "posture-20261012T1400Z", "Captured", ""],
] if EXAMPLE else [["EV-01", "Identity and role assignments (example)", "role-assignments.json", "run folder", "Captured", ""]] + blank_rows(19, 6)
end = table(ws, 4, ["ID", "What it shows", "Evidence file(s)", "Run folder", "Status", "Notes"], ev, [8, 40, 34, 26, 12, 36],
            example_rows=0 if EXAMPLE else 1, input_cols=list(range(1, 7)))
remember_csv(ws, 4, end, "config-evidence")
s0 = end + 3
ws.cell(row=s0 - 1, column=1, value="Scan method (repository and package)").font = Font(name=FONT, size=11, bold=True, color=INK)
scans = [
    ["Secrets in repository history", "gitleaks detect --source <repo> --log-opts=--all --report-format json --report-path gitleaks.json", "Zero findings, or each one a documented false positive", "gitleaks.json", ""],
    ["Vulnerabilities and misconfiguration in the release", "trivy fs --scanners vuln,secret,misconfig --severity CRITICAL,HIGH --format json -o trivy-fs.json <path>", "No Critical; every High on the Risk Register", "trivy-fs.json", ""],
    ["Container image", "trivy image --severity CRITICAL,HIGH --format json -o trivy-image.json <image>", "No Critical", "trivy-image.json", ""],
    ["Dependencies", "npm audit --json > npm-audit.json   (or the Dependabot alert export)", "No Critical; every High on the Risk Register", "npm-audit.json", ""],
]
end2 = table(ws, s0, ["Check", "Command", "Pass condition", "Output file", "Result"], scans, [8, 40, 34, 26, 12, 36], input_cols=[5])
for rr in range(s0 + 1, end2 + 1):
    ws.cell(row=rr, column=2).font = Font(name="Consolas", size=9, color=INK)

# ---------------------------------------------------------------- Logging Validation
ws = wb.create_sheet("Logging Validation")
title_block(ws, "Logging validation", "Log sources, retention, and a firing test for every alert rule. An alert is validated only when someone has received it.")
src = [
    ["Subscription activity log", "Administrative, Security, Policy, ServiceHealth", "Log Analytics workspace", "Diagnostic setting", "365 d; archive 7 y", "EV-08"],
    ["Key Vault", "AuditEvent", "Log Analytics workspace", "Diagnostic setting", "365 d", "EV-04"],
    ["Database", "SQLSecurityAuditEvents", "Log Analytics workspace", "Auditing to workspace", "365 d", "EV-03"],
    ["Application gateway / WAF", "Access, Firewall", "Log Analytics workspace", "Diagnostic setting", "365 d", "EV-02"],
    ["Entra ID", "SignInLogs, AuditLogs", "Log Analytics workspace", "Entra diagnostic setting", "365 d", "EV-01"],
] if EXAMPLE else [["Subscription activity log (example)", "Administrative, Security, Policy", "Workspace", "Diagnostic setting", "365 d", "EV-08"]] + blank_rows(11, 6)
end = table(ws, 4, ["Source", "Categories", "Destination", "Collection method", "Retention", "Evidence"], src, [30, 34, 24, 22, 18, 10],
            example_rows=0 if EXAMPLE else 1, input_cols=list(range(1, 7)))
remember_csv(ws, 4, end, "log-sources")
a0 = end + 3
ws.cell(row=a0 - 1, column=1, value="Alert firing test log").font = Font(name=FONT, size=11, bold=True, color=INK)
alerts = [
    ["Key Vault deleted", "Activity log", "Delete a throwaway vault in the sandbox, then purge it", "2026-10-14 15:02", "Platform lead", "Yes"],
    ["Policy assignment deleted", "Activity log", "Delete and recreate a test assignment in the sandbox", "2026-10-14 15:20", "Platform lead", "Yes"],
    ["NSG rule changed", "Activity log", "Add then remove a deny rule on a sandbox NSG", "2026-10-14 15:31", "Platform lead", "Yes"],
    ["Break-glass account sign-in", "Log query", "Planned sign-in with the emergency account, witnessed", "", "", ""],
    ["Backup job failed", "Backup alert", "Not safely testable; confirm rule and action group only", "n/a", "", "n/a"],
] if EXAMPLE else [["Key Vault deleted (example)", "Activity log", "Delete a throwaway vault in a sandbox", "", "", ""]] + blank_rows(19, 6)
end = table(ws, a0, ["Rule", "Type", "How to fire it safely", "Fired (UTC)", "Tester (role)", "Received?"], alerts, [30, 34, 24, 22, 18, 10],
            example_rows=0 if EXAMPLE else 1, input_cols=list(range(1, 7)))
v = DataValidation(type="list", formula1='"Yes,No,n/a"', allow_blank=True)
ws.add_data_validation(v)
v.add(f"F{a0 + 1}:F{end}")
remember_csv(ws, a0, end, "alert-test-log")

# ---------------------------------------------------------------- Summary
ws = wb.create_sheet("Summary", 1)
title_block(ws, "Summary", "Live counts from the Risk Register. Nothing to type on this sheet.")
rr = f"'Risk Register'!$H${H0 + 1}:$H${RISK_LAST}"
rs = f"'Risk Register'!$J${H0 + 1}:$J${RISK_LAST}"
heads = ["Severity", "Total", "Open", "Mitigating", "Accepted", "Closed / Mitigated"]
for c, h in enumerate(heads, 1):
    cell = ws.cell(row=4, column=c, value=h)
    cell.font, cell.fill, cell.border = HEAD, HEAD_FILL, GRID
for i, sev in enumerate(["Critical", "High", "Medium", "Low"]):
    r = 5 + i
    vals = [sev, f'=COUNTIF({rr},A{r})', f'=COUNTIFS({rr},A{r},{rs},"Open")', f'=COUNTIFS({rr},A{r},{rs},"Mitigating")',
            f'=COUNTIFS({rr},A{r},{rs},"Accepted")', f'=COUNTIFS({rr},A{r},{rs},"Closed")+COUNTIFS({rr},A{r},{rs},"Mitigated")']
    for c, v in enumerate(vals, 1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font, cell.border = (Font(name=FONT, size=10, bold=True, color="FFFFFF") if c == 1 else BODY), GRID
        if c == 1:
            cell.fill = PatternFill("solid", fgColor=SEV_FILLS[sev])
ws.cell(row=9, column=1, value="Total").font = Font(name=FONT, size=10, bold=True, color=INK)
for c in range(2, 7):
    col = get_column_letter(c)
    cell = ws.cell(row=9, column=c, value=f"=SUM({col}5:{col}8)")
    cell.font, cell.border = Font(name=FONT, size=10, bold=True, color=INK), GRID
cm = "'Compliance Mapping'!$F$5:$F$200"
ws.cell(row=11, column=1, value="Compliance mapping").font = Font(name=FONT, size=11, bold=True, color=INK)
for i, st in enumerate(["Met", "Partial", "Gap", "Not applicable"]):
    ws.cell(row=12 + i, column=1, value=st).font = BODY
    c = ws.cell(row=12 + i, column=2, value=f'=COUNTIF({cm},A{12 + i})')
    c.font, c.border = BODY, GRID
for i, w in enumerate([18, 10, 10, 12, 12, 18], 1):
    ws.column_dimensions[get_column_letter(i)].width = w

# ---------------------------------------------------------------- page setup and accent bar
for sh in wb.worksheets:
    sh.sheet_properties.tabColor = ACCENT if sh.title in ("Read Me", "Summary") else "57606A"
    sh.page_setup.orientation = "landscape"
    sh.page_setup.fitToWidth = 1
    sh.sheet_properties.pageSetUpPr.fitToPage = True

os.makedirs(OUT_DIR, exist_ok=True)
path = os.path.join(OUT_DIR, OUT_NAME)
wb.save(path)

# CSV copies of the data tables (values as typed; formula cells exported as their formula text)
csv_dir = os.path.join(OUT_DIR, "csv")
os.makedirs(csv_dir, exist_ok=True)
for sh, h, last, name in csv_sheets:
    with open(os.path.join(csv_dir, f"{name}.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for row in sh.iter_rows(min_row=h, max_row=last, values_only=True):
            if row[0] is None:
                continue
            w.writerow(["" if v is None else v for v in row])
print(path)
