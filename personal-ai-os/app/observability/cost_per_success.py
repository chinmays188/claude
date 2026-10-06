from pydantic import BaseModel


class CostPerSuccessReport(BaseModel):
    """Real join of cost against outcome -- found missing while
    investigating 'AI Cost & Latency Engineering': CostTracker/JourneyCost
    total $ per journey, but nothing ties that $ to whether the request
    actually succeeded. Built from TraceStore's own summaries (each already
    carries real status + real cost), not fabricated data."""

    successful_count: int
    failed_count: int
    total_cost_successful: float
    total_cost_failed: float

    @property
    def cost_per_success(self) -> float | None:
        """None (not 0.0) when there are no successes yet, so a caller
        can't mistake 'no data' for 'free'."""
        if self.successful_count == 0:
            return None
        return self.total_cost_successful / self.successful_count

    @property
    def cost_per_failure(self) -> float | None:
        if self.failed_count == 0:
            return None
        return self.total_cost_failed / self.failed_count

    @property
    def total_cost(self) -> float:
        return self.total_cost_successful + self.total_cost_failed

    @property
    def success_rate(self) -> float | None:
        total = self.successful_count + self.failed_count
        if total == 0:
            return None
        return self.successful_count / total


def compute_cost_per_success(trace_summaries: list[dict]) -> CostPerSuccessReport:
    """trace_summaries: dicts shaped like TraceStore.list_summaries()'s
    rows (must have 'status' and 'cost'). 'success' is status == 'success';
    anything else (e.g. 'error') counts as failed."""
    successful_count = 0
    failed_count = 0
    total_cost_successful = 0.0
    total_cost_failed = 0.0

    for summary in trace_summaries:
        cost = summary.get("cost", 0.0) or 0.0
        if summary.get("status") == "success":
            successful_count += 1
            total_cost_successful += cost
        else:
            failed_count += 1
            total_cost_failed += cost

    return CostPerSuccessReport(
        successful_count=successful_count,
        failed_count=failed_count,
        total_cost_successful=total_cost_successful,
        total_cost_failed=total_cost_failed,
    )
