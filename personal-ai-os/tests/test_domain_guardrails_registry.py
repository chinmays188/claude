import importlib

from app.domains.guardrails import DOMAIN_GUARDRAILS, rules_for_domain


def test_all_four_domains_represented():
    domains = {rule.domain for rule in DOMAIN_GUARDRAILS}

    assert domains == {"CAREER", "PM", "FINANCE", "LEARNING"}


def test_rules_for_domain_filters_correctly():
    finance_rules = rules_for_domain("finance")

    assert len(finance_rules) > 0
    assert all(r.domain == "FINANCE" for r in finance_rules)


def test_rules_for_unknown_domain_returns_empty():
    assert rules_for_domain("UNKNOWN") == []


def test_every_enforced_by_reference_resolves_to_a_real_function_module_or_class():
    """Guards against documentation drift -- if a rule's enforced_by path
    doesn't actually exist, this test fails, forcing the registry to be kept
    honest as the underlying code changes. enforced_by is a dotted path,
    optionally followed by a parenthetical explanation, and may point either
    at a module itself or at an attribute (function/class) within one."""
    for rule in DOMAIN_GUARDRAILS:
        dotted_path = rule.enforced_by.split(" ")[0]

        try:
            importlib.import_module(dotted_path)
            continue  # the whole path is itself an importable module
        except ImportError:
            pass

        module_path, _, attr = dotted_path.rpartition(".")
        module = importlib.import_module(module_path)
        assert hasattr(module, attr), f"{rule.enforced_by} does not resolve (module {module_path} has no '{attr}')"
