from app.actions.models import ActionClass, RiskLevel

# Section 27's exact example mapping. Tools not listed default to WRITE (the
# cautious middle ground) rather than READ, so a newly-added tool never
# silently skips approval just because it wasn't explicitly classified yet.
_DEFAULT_CLASSIFICATIONS: dict[str, ActionClass] = {
    "github_activity": ActionClass.READ,
    "calendar_day": ActionClass.READ,
    "email_summary": ActionClass.READ,
    "retrieve": ActionClass.READ,
    "calculator": ActionClass.READ,
    "send_email": ActionClass.ACT,
    "create_calendar_event": ActionClass.ACT,
    "modify_github": ActionClass.ACT,
    "create_draft": ActionClass.WRITE,
}

_DEFAULT_RISK: dict[ActionClass, RiskLevel] = {
    ActionClass.READ: RiskLevel.LOW,
    ActionClass.WRITE: RiskLevel.MEDIUM,
    ActionClass.ACT: RiskLevel.HIGH,
}


class ActionClassifier:
    def __init__(self, overrides: dict[str, ActionClass] | None = None):
        self._classifications = {**_DEFAULT_CLASSIFICATIONS, **(overrides or {})}

    def classify(self, tool_name: str) -> ActionClass:
        return self._classifications.get(tool_name, ActionClass.WRITE)

    def assess_risk(self, action_class: ActionClass) -> RiskLevel:
        return _DEFAULT_RISK[action_class]

    def requires_approval(self, action_class: ActionClass) -> bool:
        return action_class != ActionClass.READ
