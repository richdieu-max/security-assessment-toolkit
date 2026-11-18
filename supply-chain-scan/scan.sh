#!/usr/bin/env bash
# scan.sh  (SKELETON)
# Scans a repository or release folder for secrets, vulnerable packages,
# misconfiguration, and writes an SBOM, then triages everything into one list.
#
#   ./scan.sh <target-folder> [evidence-folder]
#
# Tools (each optional; a missing tool is recorded as skipped, never as clean):
#   gitleaks  secrets in files and git history (always with --redact)
#   trivy     OS and language package vulnerabilities, Dockerfile/IaC misconfig, secrets
#   syft      software bill of materials (SPDX JSON)
# Dependabot alerts are read if DEPENDABOT_REPO=<owner>/<repo> is set and gh is signed in.
#
# Read-only for the target. Writes only into the evidence folder.
set -euo pipefail

TARGET="${1:?usage: scan.sh <target-folder> [evidence-folder]}"
OUT="${2:-./evidence/scan-$(date -u +%Y%m%d-%H%M%SZ)}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUT"
: > "$OUT/tools.txt"

note() { echo "$*" | tee -a "$OUT/tools.txt"; }
have() { command -v "$1" >/dev/null 2>&1; }

# 1. secrets
if have gitleaks; then
  note "gitleaks $(gitleaks version 2>/dev/null || echo '?'): ran"
  gitleaks detect --source "$TARGET" --redact --no-banner --exit-code 0 \
    --report-format json --report-path "$OUT/gitleaks.json" || note "gitleaks: error"
else
  note "gitleaks: skipped (not installed)"
fi

# 2. vulnerabilities, misconfiguration, secrets
if have trivy; then
  note "trivy $(trivy --version 2>/dev/null | head -1 || echo '?'): ran"
  trivy fs --quiet --scanners vuln,misconfig,secret --exit-code 0 \
    --format json --output "$OUT/trivy.json" "$TARGET" || note "trivy: error"
else
  note "trivy: skipped (not installed)"
fi

# 3. SBOM
if have syft; then
  note "syft $(syft version 2>/dev/null | awk '/^Version/ {print $2}' || echo '?'): ran"
  syft "dir:$TARGET" -q -o "spdx-json=$OUT/sbom.spdx.json" || note "syft: error"
else
  note "syft: skipped (not installed)"
fi

# 4. Dependabot (optional)
if [ -n "${DEPENDABOT_REPO:-}" ] && have gh; then
  note "dependabot ($DEPENDABOT_REPO): read"
  gh api "repos/${DEPENDABOT_REPO}/dependabot/alerts" --paginate > "$OUT/dependabot.json" || note "dependabot: error"
else
  note "dependabot: skipped (DEPENDABOT_REPO not set or gh missing)"
fi

# 5. triage
args=(--out "$OUT")
[ -s "$OUT/gitleaks.json" ] && args+=(--gitleaks "$OUT/gitleaks.json")
[ -s "$OUT/trivy.json" ] && args+=(--trivy "$OUT/trivy.json")
[ -s "$OUT/dependabot.json" ] && args+=(--dependabot "$OUT/dependabot.json")
python3 "$HERE/triage.py" "${args[@]}"

# 6. hash everything so the evidence can be checked later
manifest_tmp="$(mktemp)"
( cd "$OUT" && find . -maxdepth 1 -type f ! -name MANIFEST.sha256 -printf '%f\n' | sort | xargs sha256sum ) > "$manifest_tmp"
mv "$manifest_tmp" "$OUT/MANIFEST.sha256"
echo "manifest: $OUT/MANIFEST.sha256"
