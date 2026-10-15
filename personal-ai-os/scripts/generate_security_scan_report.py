"""Generates a REAL security scan report for the dashboard, closing a
gap "AI Safety & Guardrails" disclosed: "the security scanner itself
remains unextended."

Runs the real, now-extended app/platform/security_testing.py against
this project's actual source (SQL injection, SSRF, path traversal,
hardcoded secrets, dangerous calls) AND its real installed dependencies
(scan_dependencies(), via pip-audit -- real CVE data, not fabricated).

Needs a real network call (pip-audit queries the PyPA advisory
database) and takes a few seconds to run against this project's full
dependency tree, so it's pre-generated and committed rather than run on
every dashboard page render.

Usage:
    PYTHONPATH=. python scripts/generate_security_scan_report.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.platform.security_testing import scan_dependencies, scan_directory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "app" / "dashboard_ui" / "security_scan_report.json"


def main() -> None:
    print("Scanning this project's own source (app/, scripts/)...")
    code_findings = scan_directory(PROJECT_ROOT / "app") + scan_directory(PROJECT_ROOT / "scripts")
    print(f"  {len(code_findings)} real findings.")

    print("Scanning real installed dependencies via pip-audit (needs network)...")
    try:
        dependency_findings = scan_dependencies()
        dependency_scan_failed = False
    except RuntimeError as exc:
        print(f"  pip-audit failed: {exc}")
        dependency_findings = []
        dependency_scan_failed = True
    print(f"  {len(dependency_findings)} real dependency vulnerabilities found.")

    output = {
        "code_findings": [f.model_dump() for f in code_findings],
        "dependency_findings": [f.model_dump() for f in dependency_findings],
        "dependency_scan_failed": dependency_scan_failed,
    }
    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nWrote real security scan report to {OUT_PATH}")


if __name__ == "__main__":
    main()
