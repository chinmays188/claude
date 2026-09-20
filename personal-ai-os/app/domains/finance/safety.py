class TradeExecutionForbiddenError(Exception):
    pass


def execute_trade(*args, **kwargs):
    """Section 25: 'Never execute trades.' This function exists solely to
    guarantee that if anything ever calls it (a hallucinated tool call, a
    coding mistake, a future refactor), it fails loudly instead of silently
    doing nothing or, worse, actually trading. There is no working trade
    execution path anywhere in Finance OS."""
    raise TradeExecutionForbiddenError(
        "Finance OS is decision-support only (Section 19/25) — trade execution is never permitted."
    )


def transfer_funds(*args, **kwargs):
    """Section 25: 'Never transfer money.' Same guarantee as execute_trade()."""
    raise TradeExecutionForbiddenError(
        "Finance OS is decision-support only (Section 19/25) — fund transfers are never permitted."
    )
