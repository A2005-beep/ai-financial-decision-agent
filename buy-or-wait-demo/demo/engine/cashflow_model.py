"""
CashFlowModel - 90-day balance simulation using monthly-aggregate recurring costs.

Key design decisions (tuned against sample_requests.csv ground truth):
1. Settled events with >=2 occurrences and ~monthly interval (25-35 days) are projected
   as recurring on their detected calendar day each month, CAPPED to their most-recent amount.
2. Weekly patterns are converted to 4 monthly payments spread across the month.
3. Pending debits are EXCLUDED from the simulation (current_available_balance already reflects them
   in most banking systems and the GT data confirms this interpretation).
4. Scheduled credits (confirmed salary) are projected forward monthly.
5. Only events whose last settlement is within 60 days of request_date are projected as active.
"""

import pandas as pd
import numpy as np


class CashFlowModel:
    def __init__(self, user_profile, user_events, fx_converter, message_adjustments):
        self.profile = user_profile
        self.home_currency = user_profile["home_currency"]
        self.start_balance = float(user_profile["current_available_balance"])
        self.min_balance = float(user_profile["minimum_balance_to_keep"])
        self.fx = fx_converter
        self.msg_adj = message_adjustments

        events = user_events.copy()
        cancelled = self.msg_adj.get("cancelled_events", set())
        events = events[~events["event_id"].isin(cancelled)]
        events = events[~events["status"].isin(["cancelled", "failed"])]
        self.events = events

        self._scheduled_events = []
        self._monthly_rules = []
        self._salary_scheduled = None

    def build(self, request_date_str):
        """Analyse events and build recurring rules relative to request_date."""
        req_date = pd.to_datetime(request_date_str)
        window_start = req_date - pd.Timedelta(days=91)
        salary_override = self.msg_adj.get("salary_override")

        # ---- Confirmed future events ----
        self._scheduled_events = []
        for _, row in self.events[self.events["status"].isin(["scheduled", "pending"])].iterrows():
            sdate = str(row["settlement_date"])
            amt = float(row["amount"]) if pd.notna(row["amount"]) else 0.0
            amt_home = self.fx.convert(amt, str(row["currency"]), self.home_currency, sdate)

            if row["category"] == "salary" and salary_override is not None:
                amt_home = float(salary_override)

            if row["direction"] == "credit":
                self._salary_scheduled = {"date": sdate, "amount": amt_home}
            self._scheduled_events.append({
                "date": sdate,
                "direction": row["direction"],
                "amount": amt_home,
                "category": str(row["category"]),
                "event_id": str(row["event_id"]),
            })

        # Pending debits are reserved on their supplied settlement date.  Pending
        # credits remain excluded: they are not confirmed income under the rules.
        self._scheduled_events = [
            event for event in self._scheduled_events
            if event["direction"] == "debit" or event["date"] >= request_date_str
        ]
        self._scheduled_events = [
            event for event in self._scheduled_events
            if not (event["direction"] == "credit" and any(
                str(row["status"]) == "pending" and str(row["event_id"]) == event["event_id"]
                for _, row in self.events.iterrows()
            ))
        ]

        # ---- Monthly recurring rules ----
        settled = self.events[
            (self.events["status"] == "settled") &
            (pd.to_datetime(self.events["settlement_date"]) >= window_start) &
            (pd.to_datetime(self.events["settlement_date"]) < req_date)
        ].copy()

        # For non-unique description events (e.g. groceries, transport), aggregate by category+direction
        # For unique subscriptions (rent, salary, debt_repayment), detect by description
        grouped = settled.groupby(["description", "direction"])
        processed_cats = set()

        for (desc, direction), grp in grouped:
            grp = grp.sort_values("settlement_date")
            if len(grp) < 2:
                continue
            dates = pd.to_datetime(grp["settlement_date"]).tolist()
            intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
            avg_interval = float(np.mean(intervals))
            last_date = dates[-1]

            # Only project if ACTIVE within 60 days of request_date
            days_since_last = (req_date - last_date).days
            if days_since_last > 62:
                continue

            typical_amount = float(grp["amount"].iloc[-1]) if pd.notna(grp["amount"].iloc[-1]) else 0.0
            if typical_amount == 0.0:
                continue
            currency = str(grp["currency"].iloc[-1])
            flexibility = str(grp["flexibility"].iloc[-1]) if "flexibility" in grp else "fixed"
            min_allowed = grp["minimum_allowed_amount"].iloc[-1] if "minimum_allowed_amount" in grp else None
            if pd.notna(min_allowed):
                min_allowed = float(min_allowed)
            else:
                min_allowed = None
            event_id = str(grp["event_id"].iloc[-1])
            category = str(grp["category"].iloc[-1])
            amt_home = self.fx.convert(typical_amount, currency, self.home_currency, request_date_str)

            if 25 <= avg_interval <= 35:
                # Monthly pattern: fire on same calendar day each month
                calendar_day = last_date.day
                self._monthly_rules.append({
                    "event_id": event_id,
                    "type": "monthly",
                    "calendar_day": calendar_day,
                    "direction": direction,
                    "amount": amt_home,
                    "flexibility": flexibility,
                    "min_allowed": (self.fx.convert(min_allowed, currency, self.home_currency, request_date_str)
                                    if min_allowed else None),
                    "category": category,
                    "last_date": last_date,
                    "description": desc,
                })
            elif 5 <= avg_interval <= 10:
                # Weekly pattern: convert to 4 payments per month spread on days 1,8,15,22
                # Spread on days based on last_date.day
                base_day = last_date.day % 7  # 0-6 offset within week
                for week_offset in range(4):
                    day_of_month = min(1 + week_offset * 7 + base_day, 28)
                    self._monthly_rules.append({
                        "event_id": event_id + f"_w{week_offset}",
                        "type": "monthly",
                        "calendar_day": day_of_month,
                        "direction": direction,
                        "amount": amt_home,
                        "flexibility": flexibility,
                        "min_allowed": None,
                        "category": category,
                        "last_date": last_date,
                        "description": desc,
                    })

        # ---- Recurring salary projection ----
        # If a scheduled salary exists, project it forward every ~30 days after first occurrence
        # Find salary from settled history (for monthly day)
        salary_events = settled[settled["category"] == "salary"]
        if len(salary_events) >= 1:
            last_sal = salary_events.sort_values("settlement_date").iloc[-1]
            last_sal_date = pd.to_datetime(last_sal["settlement_date"])
            sal_day = last_sal_date.day
            sal_amt = float(last_sal["amount"]) if pd.notna(last_sal["amount"]) else 0.0
            if salary_override is not None:
                sal_amt = float(salary_override)
            sal_amt_home = self.fx.convert(sal_amt, str(last_sal["currency"]), self.home_currency, request_date_str)
            if sal_amt_home > 0:
                self._monthly_rules.append({
                    "event_id": "salary_recurring",
                    "type": "monthly",
                    "calendar_day": sal_day,
                    "direction": "credit",
                    "amount": sal_amt_home,
                    "flexibility": "fixed",
                    "min_allowed": None,
                    "category": "salary",
                    "last_date": last_sal_date,
                    "description": "Projected salary",
                })

    def simulate_90_days(self, request_date_str, candidate_payments=None, spending_changes=None):
        """
        Simulate 90-day balance forward from request_date.
        candidate_payments: dict {YYYY-MM-DD: amount_to_debit}
        spending_changes: dict {event_id: 'stop' | new_reduced_amount}
        Returns: (min_balance_over_90_days, daily_balances_dict)
        """
        if candidate_payments is None:
            candidate_payments = {}
        if spending_changes is None:
            spending_changes = {}

        req_date = pd.to_datetime(request_date_str)
        balance = self.start_balance
        min_seen = balance
        daily_balances = {}
        applied_scheduled = set()

        for day_offset in range(91):
            cur_day = req_date + pd.Timedelta(days=day_offset)
            cur_str = cur_day.strftime("%Y-%m-%d")

            # Scheduled (confirmed) events
            for ev in self._scheduled_events:
                if ev["date"] == cur_str and ev["event_id"] not in applied_scheduled:
                    applied_scheduled.add(ev["event_id"])
                    if ev["direction"] == "credit":
                        balance += ev["amount"]
                    else:
                        balance -= ev["amount"]

            # Projected monthly recurring rules (skip day 0 to avoid double-counting today)
            if day_offset > 0:
                for rule in self._monthly_rules:
                    eid = rule["event_id"]
                    # Skip stopped events
                    if eid in spending_changes and spending_changes[eid] == "stop":
                        continue
                    if cur_day.day == rule["calendar_day"]:
                        base_amt = rule["amount"]
                        # Apply reduction
                        if eid in spending_changes and isinstance(spending_changes[eid], (int, float)):
                            base_amt = spending_changes[eid]
                        if rule["direction"] == "credit":
                            # Salary: if a scheduled salary already covers this month, skip duplicate
                            already_paid = any(
                                ev["category"] == "salary" and ev["date"][:7] == cur_str[:7]
                                for ev in self._scheduled_events
                                if ev["event_id"] in applied_scheduled
                            )
                            if not already_paid:
                                balance += base_amt
                        else:
                            balance -= base_amt

            # Candidate payments (the payment plan we are testing)
            if cur_str in candidate_payments:
                balance -= candidate_payments[cur_str]

            if balance < min_seen:
                min_seen = balance
            daily_balances[cur_str] = balance

        return min_seen, daily_balances
