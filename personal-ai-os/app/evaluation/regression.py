from pydantic import BaseModel


class MetricSnapshot(BaseModel):
    version: str
    metrics: dict[str, float]


class RegressionFinding(BaseModel):
    metric: str
    previous: float
    current: float
    delta: float


class RegressionReport(BaseModel):
    previous_version: str
    current_version: str
    regressions: list[RegressionFinding]
    improvements: list[RegressionFinding]

    @property
    def has_regression(self) -> bool:
        return len(self.regressions) > 0


def compare(
    previous: MetricSnapshot, current: MetricSnapshot, tolerance: float = 0.0
) -> RegressionReport:
    """Compare two metric snapshots. A drop beyond `tolerance` on ANY shared metric
    counts as a regression — an improvement on one metric never excuses a drop on
    another (Section 14: don't call it an improvement just because one metric rose)."""
    regressions = []
    improvements = []

    shared_metrics = set(previous.metrics) & set(current.metrics)
    for metric in sorted(shared_metrics):
        prev_value = previous.metrics[metric]
        curr_value = current.metrics[metric]
        delta = curr_value - prev_value
        finding = RegressionFinding(metric=metric, previous=prev_value, current=curr_value, delta=delta)

        if delta < -tolerance:
            regressions.append(finding)
        elif delta > tolerance:
            improvements.append(finding)

    return RegressionReport(
        previous_version=previous.version,
        current_version=current.version,
        regressions=regressions,
        improvements=improvements,
    )
