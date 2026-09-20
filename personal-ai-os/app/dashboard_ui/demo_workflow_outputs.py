"""Fabricated demo values for dashboard fields that are caller-supplied from
domain workflow outputs rather than persisted in any store (see
app/dashboard/domain_data.py's docstrings — resume_readiness, feedback
themes, portfolio value, learning progress, etc. all come from Career/PM/
Finance/Learning OS's own workflow runs, which this demo doesn't actually
execute against the live Gemini API on every dashboard page load).

Kept as a single, clearly-labeled module rather than scattered literals
inside the UI code, and clearly separate from the real, persisted data the
seed script writes into SQLite."""

CAREER_DEMO = {
    "applications": 6,
    "resume_readiness": 0.8,
    "interview_readiness": 0.55,
    "skill_gaps": ["System design depth", "MLOps fundamentals"],
}

PM_DEMO = {
    "feedback_themes": ["Refund processing delays", "Support handoff friction"],
    "open_requests": 4,
    "sprint_status": "on_track",
    "commitments_count": 2,
    "project_risks": ["Refund automation PRD still pending final sign-off"],
}

FINANCE_DEMO = {
    "portfolio_value": 18500.0,
    "allocation": {"equity": 0.65, "debt": 0.25, "cash": 0.10},
    "loans_count": 0,
    "risk_indicators": ["Equity concentration above 60%"],
}

LEARNING_DEMO = {
    "current_subjects": ["Kubernetes", "System Design"],
    "progress": {"Kubernetes": 7.5, "Docker": 9.0},
    "knowledge_gaps": ["Kubernetes networking", "Ingress controllers"],
    "exercises_completed": 12,
    "assessment_scores": {"Docker quiz": 8.5, "Kubernetes quiz": 6.5},
}
