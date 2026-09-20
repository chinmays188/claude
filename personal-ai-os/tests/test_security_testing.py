from pathlib import Path

from app.platform.security_testing import (
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
