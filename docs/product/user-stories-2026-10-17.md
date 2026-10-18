# Target user stories (2026-10-17)

Owner input, pasted in session on 2026-10-17 from a teammate's list. Typos are corrected; the
teammate's notes in Filipino are translated in brackets. This is an input to strategy, not a recorded
scope change: the [product shape record](../work/product-shape-2026-10-17/strategy.md) reads each
story against the framing and marks it adopt, reframe or defer.

## 1. Market monitoring and situational awareness (trader)

1. **Unified market monitoring.** As a trader, I want to monitor WESM prices, system demand, available
   generation capacity and grid condition in one dashboard, so I can quickly understand the current
   market condition.
2. **Price spike or collapse detection.** I want an alert when the market price passes the average or a
   configurable threshold, and to identify the driving factor (demand, supply, fuel and so on).
3. **Supply and outage intelligence.** As a trader, I want to identify generating plant outages,
   capacity reductions and grid constraints, to anticipate possible price movement.

## 2. Ontology-driven market intelligence (portfolio manager)

4. **Trace market events to portfolio impact.** As a portfolio manager, I want to trace a market event
   through the affected grid condition, prices, contracts [note: "or skip this for now"] and customer
   position, so I can understand which part of my portfolio is affected (for example, Visayas
   accounts).
5. **Explain why an alert was triggered.** I want the system to explain why the alert was triggered and
   which connected contribution was related to it, so I can validate the risk before acting.
6. **Ask cross-domain questions.** I want to ask questions in natural language about market conditions
   and the portfolio, so I can investigate risks without searching multiple systems. Example: which
   customers are exposed to higher Luzon prices tomorrow evening?
7. **Discover indirect relationships.** As a risk analyst, I want to discover indirect relationships
   between market events and portfolio positions, so I can identify risks that are not obvious from an
   individual data feed. [Note: "And can it validate if our portfolio position is correct?"]

## 3. Portfolio exposure and profitability

8. **Identify unhedged volume.** As a trader, I want to identify the volume exposed to the market
   (hours, rate and so on).
9. **Quantify financial exposure.** As a portfolio manager, I want to estimate the financial impact of
   market prices on unhedged volume, so I can prioritize the risks with the greatest potential effect on
   gross profit.
10. **Explain profit and loss deterioration.** As a portfolio manager, I want to identify the market
    events, customers, contracts and trading intervals that contribute to a decline in portfolio
    profitability, so I can determine the root causes of losses.
11. **Forecast portfolio risk** [note: "but optional, this seems to take us too far"]. As a risk
    analyst, I want to simulate different market price, demand and supply conditions, so I can estimate
    how alternative scenarios could affect portfolio profitability.
12. **Maintain traceability and auditability.** As a risk manager, I want to trace every material alert
    and financial estimate to its source data, relationships, calculation logic and model version, so I
    can validate results and support internal reviews.
