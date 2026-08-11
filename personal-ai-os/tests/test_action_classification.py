from app.actions.classification import ActionClassifier
from app.actions.models import ActionClass, RiskLevel


def test_read_github_classified_as_read():
    classifier = ActionClassifier()

    assert classifier.classify("github_activity") == ActionClass.READ


def test_send_email_classified_as_act():
    classifier = ActionClassifier()

    assert classifier.classify("send_email") == ActionClass.ACT


def test_create_draft_classified_as_write():
    classifier = ActionClassifier()

    assert classifier.classify("create_draft") == ActionClass.WRITE


def test_modify_github_classified_as_act():
    classifier = ActionClassifier()

    assert classifier.classify("modify_github") == ActionClass.ACT


def test_unknown_tool_defaults_to_write_not_read():
    classifier = ActionClassifier()

    assert classifier.classify("some_new_tool_nobody_classified_yet") == ActionClass.WRITE


def test_read_never_requires_approval():
    classifier = ActionClassifier()

    assert classifier.requires_approval(ActionClass.READ) is False


def test_write_and_act_require_approval():
    classifier = ActionClassifier()

    assert classifier.requires_approval(ActionClass.WRITE) is True
    assert classifier.requires_approval(ActionClass.ACT) is True


def test_risk_increases_with_action_class():
    classifier = ActionClassifier()

    assert classifier.assess_risk(ActionClass.READ) == RiskLevel.LOW
    assert classifier.assess_risk(ActionClass.WRITE) == RiskLevel.MEDIUM
    assert classifier.assess_risk(ActionClass.ACT) == RiskLevel.HIGH


def test_overrides_take_precedence_over_defaults():
    classifier = ActionClassifier(overrides={"github_activity": ActionClass.ACT})

    assert classifier.classify("github_activity") == ActionClass.ACT
