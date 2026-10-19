# Method

How I run a cloud infrastructure security assessment with this workbook. The steps follow the sheet order.

## 1. Agree the scales before the first finding

Fill in the Rating Matrix with the system owner, in their words. "Severe impact" should name the data that matters in this environment, not a generic definition. Agree the severity bands and the response each one requires. Changing a band later re-rates every risk automatically, but arguing about severity after findings exist turns every rating into a negotiation.

## 2. Model the system

On the Threat Model sheet:

1. **Assets.** What an attacker wants and where it lives: data stores, secrets, keys, backups, logs, administrator identities.
2. **Trust boundaries.** Every place data or control crosses from one trust level to another, with the entry points that cross it and whether the protection is built.
3. **STRIDE at each boundary.** For each boundary, the Spoofing, Tampering, Repudiation, Information disclosure, Denial of service and Elevation of privilege threats that apply, the control in place, and the gap. A gap becomes a Risk Register row and its ID goes back in the last column.

## 3. Record findings

One finding per Risk Register row. Type only Likelihood and Impact; the sheet computes Score and Severity. Write the "Action to close" as something a person can do, and give it a role and a due date. Status moves Open → Mitigating → Mitigated or Closed, or Accepted with a written acceptance.

## 4. Inventory what was built

The Control Register lists every rule, policy, role, network rule and alert, in plain English: where it lives, what it does, why it exists, and how it is enforced (deny, modify, audit, RBAC, configuration). Each row maps to NIST SP 800-53 Rev. 5, NIST CSF 2.0 and ISO/IEC 27001:2022 Annex A, and cites evidence.

## 5. Map to frameworks

The Compliance Mapping sheet rolls the control register up to CSF 2.0 categories. A category is **Met** only when its controls are built and evidenced, **Partial** when a gap is recorded on the Risk Register, and **Gap** when nothing is in place. The mapping shows a control *supports* an objective; it is not a certification or an attestation.

## 6. Collect evidence

Evidence comes from read-only collection runs, each in its own folder with a SHA-256 manifest, so anyone can check the files were not edited afterwards. The scan method table covers the repository and release package: secrets in git history, vulnerabilities and misconfiguration, container images and dependencies.

## 7. Validate logging

List every log source, its destination and retention. Then fire each alert rule in a way that does not harm production (delete a throwaway resource in a sandbox, change and revert a test rule) and record when, by whom, and whether the notification arrived. Rules that cannot be fired safely are marked n/a with the reason.

## 8. Report

The Summary sheet gives the counts for the executive summary. The findings report follows the Risk Register order: Critical and High first, each with the asset, the evidence, the action and the owner role.
