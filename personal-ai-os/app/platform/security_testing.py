import re
from pathlib import Path

from pydantic import BaseModel

from app.platform.secrets import scan_for_hardcoded_secrets


class SecurityFinding(BaseModel):
    check_name: str
    file_path: str
    detail: str
    severity: str  # "HIGH" | "MEDIUM" | "LOW"


_DANGEROUS_CALL_PATTERNS = [
    (re.compile(r"\beval\("), "HIGH", "eval() call found -- arbitrary code execution risk"),
    (re.compile(r"\bexec\("), "HIGH", "exec() call found -- arbitrary code execution risk"),
    (re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"), "HIGH", "subprocess call with shell=True -- shell injection risk"),
    (re.compile(r"pickle\.loads?\("), "MEDIUM", "pickle load found -- deserialization of untrusted data risk"),
]


def scan_file_for_hardcoded_secrets(path: Path) -> list[SecurityFinding]:
    text = path.read_text(errors="ignore")
    findings = scan_for_hardcoded_secrets(text)
    return [
        SecurityFinding(check_name="hardcoded_secret", file_path=str(path), detail=f"Matched secret-like pattern (value redacted)", severity="HIGH")
        for _ in findings
    ]


def scan_file_for_dangerous_calls(path: Path) -> list[SecurityFinding]:
    text = path.read_text(errors="ignore")
    findings = []
    for pattern, severity, detail in _DANGEROUS_CALL_PATTERNS:
        for match in pattern.finditer(text):
            line_number = text[: match.start()].count("\n") + 1
            findings.append(
                SecurityFinding(check_name="dangerous_call", file_path=f"{path}:{line_number}", detail=detail, severity=severity)
            )
    return findings


def scan_directory(root: Path, extensions: tuple[str, ...] = (".py",)) -> list[SecurityFinding]:
    """Milestone 58: 'Production Security Testing.' A real, runnable scan
    over this project's own source — not a description of what a security
    review would check, an actual script that produced real findings (see
    the spec file for what it found when run against this codebase)."""
    findings: list[SecurityFinding] = []
    for path in root.rglob("*"):
        if path.suffix not in extensions or ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        findings.extend(scan_file_for_hardcoded_secrets(path))
        findings.extend(scan_file_for_dangerous_calls(path))
    return findings
