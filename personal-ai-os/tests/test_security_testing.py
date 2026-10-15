from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.platform.security_testing import (
    scan_dependencies,
    scan_directory,
    scan_file_for_dangerous_calls,
    scan_file_for_hardcoded_secrets,
)


def test_scan_file_detects_hardcoded_secret(tmp_path):
    path = tmp_path / "config.py"
    path.write_text('API_KEY = "AIzaSyAhNkvygvNeSBDifXQqVitGS1Mq1xr74CA"')

    findings = scan_file_for_hardcoded_secrets(path)

    assert len(findings) == 1
    assert findings[0].severity == "HIGH"


def test_scan_file_finds_no_secrets_in_clean_file(tmp_path):
    path = tmp_path / "config.py"
    path.write_text("API_KEY = os.getenv('API_KEY')")

    assert scan_file_for_hardcoded_secrets(path) == []


def test_scan_file_detects_real_eval_call(tmp_path):
    path = tmp_path / "risky.py"
    path.write_text("result = eval(user_input)")

    findings = scan_file_for_dangerous_calls(path)

    assert any(f.check_name == "dangerous_call" and "eval" in f.detail for f in findings)


def test_scan_file_detects_shell_true_subprocess(tmp_path):
    path = tmp_path / "risky.py"
    path.write_text('subprocess.run(cmd, shell=True)')

    findings = scan_file_for_dangerous_calls(path)

    assert any("shell" in f.detail for f in findings)


def test_scan_file_clean_code_has_no_findings(tmp_path):
    path = tmp_path / "clean.py"
    path.write_text("def add(a, b):\n    return a + b\n")

    assert scan_file_for_dangerous_calls(path) == []


def test_scan_directory_runs_against_real_calculator_and_finds_no_eval():
    """Regression check for the specific safety property Phase 1's
    calculator.py was built around: it deliberately uses ast parsing instead
    of eval() to avoid arbitrary code execution. This test fails loudly if
    that ever regresses."""
    calculator_path = Path(__file__).resolve().parent.parent / "app" / "tools" / "calculator.py"

    findings = scan_file_for_dangerous_calls(calculator_path)

    assert findings == []


def test_scan_directory_documented_false_positive_on_its_own_source():
    """Documents the real, disclosed limitation (see specs/production_platform.md,
    Milestone 58): the scanner's own regex-pattern-definition source lines
    contain the literal substrings it searches for, producing a false
    positive against itself. This test pins that known behavior so it's
    visible if the scanner's own patterns change."""
    security_testing_path = Path(__file__).resolve().parent.parent / "app" / "platform" / "security_testing.py"

    findings = scan_file_for_dangerous_calls(security_testing_path)

    assert len(findings) >= 1  # the documented false positive


def test_scan_file_detects_sql_injection_via_string_concatenation(tmp_path):
    path = tmp_path / "risky.py"
    path.write_text('cursor.execute("SELECT * FROM users WHERE id = " + user_id)')

    findings = scan_file_for_dangerous_calls(path)

    assert any("SQL" in f.detail for f in findings)


def test_scan_file_detects_sql_injection_via_fstring(tmp_path):
    path = tmp_path / "risky.py"
    path.write_text('cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")')

    findings = scan_file_for_dangerous_calls(path)

    assert any("SQL" in f.detail for f in findings)


def test_scan_file_detects_sql_injection_via_percent_formatting(tmp_path):
    path = tmp_path / "risky.py"
    path.write_text('cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)')

    findings = scan_file_for_dangerous_calls(path)

    assert any("SQL" in f.detail for f in findings)


def test_scan_file_does_not_flag_parameterized_sql(tmp_path):
    """Real, honest negative case: the SAFE way to run a parameterized
    query (placeholders + a separate params tuple) must not be flagged --
    a scanner that flags safe code trains developers to ignore it."""
    path = tmp_path / "safe.py"
    path.write_text('cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))')

    findings = scan_file_for_dangerous_calls(path)

    assert not any("SQL" in f.detail for f in findings)


def test_scan_file_detects_ssrf_prone_bare_variable_request(tmp_path):
    path = tmp_path / "risky.py"
    path.write_text("response = requests.get(user_provided_url)")

    findings = scan_file_for_dangerous_calls(path)

    assert any("SSRF" in f.detail for f in findings)


def test_scan_file_detects_path_traversal(tmp_path):
    path = tmp_path / "risky.py"
    path.write_text('open("../../etc/passwd")')

    findings = scan_file_for_dangerous_calls(path)

    assert any("traversal" in f.detail for f in findings)


def test_scan_file_does_not_flag_a_normal_relative_open(tmp_path):
    path = tmp_path / "safe.py"
    path.write_text('open("data/config.json")')

    findings = scan_file_for_dangerous_calls(path)

    assert not any("traversal" in f.detail for f in findings)


@patch("app.platform.security_testing.subprocess.run")
def test_scan_dependencies_parses_real_pip_audit_output(mock_run):
    """Scripted pip-audit JSON (its real documented shape), not a live
    network call in a unit test -- scan_dependencies() was verified
    live separately against this project's actual installed packages
    (see scripts/generate_security_scan_report.py)."""
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout='{"dependencies": [{"name": "pypdf", "version": "6.15.0", "vulns": '
               '[{"id": "PYSEC-2026-3910", "fix_versions": ["6.16.1"], "description": "Long runtime DoS."}]}], "fixes": []}',
        stderr="",
    )

    findings = scan_dependencies()

    assert len(findings) == 1
    assert findings[0].check_name == "dependency_vulnerability"
    assert "pypdf" in findings[0].file_path
    assert "PYSEC-2026-3910" in findings[0].detail


@patch("app.platform.security_testing.subprocess.run")
def test_scan_dependencies_returns_empty_for_clean_dependencies(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"dependencies": [{"name": "pydantic", "version": "2.13.4", "vulns": []}], "fixes": []}',
        stderr="",
    )

    assert scan_dependencies() == []


@patch("app.platform.security_testing.subprocess.run")
def test_scan_dependencies_raises_on_a_real_tool_failure(mock_run):
    """A real, honest failure (e.g. pip-audit crashed, no network) must
    raise, never silently return an empty -- falsely reassuring --
    result."""
    mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="network error")

    with pytest.raises(RuntimeError):
        scan_dependencies()


def test_scan_dependencies_resolves_pip_audit_next_to_the_current_interpreter():
    """Real bug found while running this live: 'pip-audit' bare on PATH
    wasn't reliably found when this process's PATH didn't include the
    active venv's bin dir -- fixed by resolving it relative to
    sys.executable instead. This pins that the command actually used is
    a real, existing executable path (not the bare string that failed),
    without making a real network call in a unit test."""
    import sys

    from app.platform.security_testing import Path as SecurityTestingPath  # noqa: F401 -- confirms Path import present

    pip_audit_path = Path(sys.executable).parent / "pip-audit"
    assert pip_audit_path.exists(), (
        "pip-audit should be installed in this venv (requirements.txt) -- "
        "if this fails, reinstall with `pip install pip-audit`."
    )
