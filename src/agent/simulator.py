from __future__ import annotations

from typing import Literal

SimulatedType = Literal["customer_validation", "step_up_auth", "analyst_info"]


def simulate_evidence_response(
    request_type: SimulatedType,
    *,
    flagged_amount: float,
    customer_median_amount: float,
    is_new_device: bool,
) -> str:
    """Simulate the response a customer/analyst would plausibly give, grounded in the
    actual transaction data rather than invented freely. State the assumption plainly --
    callers must log this string verbatim into evidence_requests.assumed_response.

    Bug fix (2026-09-24), found live by an external diagnostic run
    (TASK14_ALL_FRAUD_DIAGNOSTIC.md) against a full 20-case batch: this
    function used to also take `fraud_probability` and OR it into
    `looks_anomalous` (`fraud_probability > 0.6`). That made the simulated
    "independent" customer evidence circular -- the model's own uncertain
    assessment (e.g. 0.62) decided that the simulated customer should deny
    the transaction, and that denial was then fed back into reassess_node
    as new evidence, pushing the probability even higher (real examples
    from the diagnosed batch: 0.62->0.93, 0.48->0.94, 0.68->0.86). A
    genuinely independent signal can't be a function of the thing it's
    supposed to be corroborating. The simulated response is now driven
    only by graph facts (amount deviation, new-device flag) -- neither of
    which the LLM's probability estimate can influence.
    """
    amount_ratio = flagged_amount / customer_median_amount if customer_median_amount else 999
    looks_anomalous = amount_ratio > 3 or is_new_device

    if request_type == "customer_validation":
        if looks_anomalous:
            return (
                f"Customer states they did not make this ${flagged_amount:.2f} purchase "
                f"and still has the card. (Simulated: amount is {amount_ratio:.1f}x their "
                f"typical transaction{' from a device new to this account' if is_new_device else ''}.)"
            )
        return (
            f"Customer confirms they made this ${flagged_amount:.2f} purchase. "
            f"(Simulated: amount is in line with their typical spending pattern.)"
        )

    if request_type == "step_up_auth":
        if looks_anomalous:
            return "Step-up authentication failed / was not completed. (Simulated: anomalous activity pattern.)"
        return "Step-up authentication completed successfully. (Simulated: activity fits customer's normal pattern.)"

    return "Analyst confirms no additional context beyond the graph evidence is available. (Simulated.)"
