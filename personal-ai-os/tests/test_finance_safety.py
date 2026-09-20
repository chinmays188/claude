import pytest

from app.domains.finance.safety import TradeExecutionForbiddenError, execute_trade, transfer_funds
from app.evaluation.finance_eval import check_no_trade_execution_capability


def test_execute_trade_always_raises():
    with pytest.raises(TradeExecutionForbiddenError):
        execute_trade()


def test_execute_trade_raises_regardless_of_arguments():
    with pytest.raises(TradeExecutionForbiddenError):
        execute_trade("BUY", "AAPL", 100)


def test_transfer_funds_always_raises():
    with pytest.raises(TradeExecutionForbiddenError):
        transfer_funds(amount=1000, to_account="12345")


def test_check_no_trade_execution_capability_passes():
    result = check_no_trade_execution_capability()

    assert result.passed
