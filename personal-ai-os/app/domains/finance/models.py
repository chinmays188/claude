from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class AssetClass(str, Enum):
    EQUITY = "equity"
    DEBT = "debt"
    CASH = "cash"
    REAL_ESTATE = "real_estate"
    COMMODITY = "commodity"
    CRYPTO = "crypto"


class ClaimKind(str, Enum):
    """Section 23: 'The system must distinguish FACT, CALCULATION, ASSUMPTION,
    OPINION.' Every statement the Finance OS produces about the user's money
    must be tagged with exactly one of these — this is the single most
    important structural rule in Finance OS."""

    FACT = "FACT"  # a value taken directly from the user's actual data
    CALCULATION = "CALCULATION"  # a deterministic derivation from FACTs (Section 24: never LLM arithmetic)
    ASSUMPTION = "ASSUMPTION"  # an input the analysis depends on that isn't itself a FACT (e.g. an assumed return rate)
    OPINION = "OPINION"  # a judgment call / recommendation, not a number


class Holding(BaseModel):
    asset: str
    asset_class: AssetClass
    quantity: float
    cost_basis: float
    current_value: float


class Portfolio(BaseModel):
    owner_id: str
    as_of: date
    holdings: list[Holding] = Field(default_factory=list)


class Goal(BaseModel):
    goal_id: str
    title: str
    target_amount: float
    target_date: date
    current_amount: float = 0.0


class Loan(BaseModel):
    loan_id: str
    principal: float
    annual_rate: float  # as a decimal, e.g. 0.08 for 8%
    remaining_term_months: int
    monthly_payment: float


class TaggedClaim(BaseModel):
    """One statement in a Finance OS output, explicitly tagged per Section 23."""

    text: str
    kind: ClaimKind
    value: float | None = None  # populated for FACT/CALCULATION claims
