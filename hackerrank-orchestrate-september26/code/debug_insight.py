# KEY INSIGHT from debugging:
# 1. "Vehicle charging" only appeared twice (2023-12-09 and 2023-12-16) - it should NOT be 
#    projected as weekly recurring because it was not a persistent pattern - it STOPPED.
#    The user switched to other transport methods (local taxi, commuter pass, etc).
#    A better heuristic: only project recurring if the LAST occurrence was within ~45 days of request_date
#    OR the event was tagged as a "subscription" type.
#
# 2. The transport costs are ~400-560 ZAR per event, happening ~weekly
#    but with DIFFERENT descriptions, so they are one-off per description.
#    The REAL monthly transport total is roughly: (all transport debits in last month) / 1
#    = e.g. 406.54 + 488.36 + 424.56 + 549.05 = ~1868 per month
#    Let's estimate: user_01 transport total monthly = sum of transport in Feb 2024 ~1868
#    vs our current model projecting 13 * 534.56 = ~6949 over 90 days = ~2317/month
#    That's somewhat close but the description-based matching is too aggressive for weekly
#
# 3. SIMPLER APPROACH: Use a monthly "bucket" approach for non-subscription categories
#    Instead of tracking individual recurring rules, compute:
#    - Average monthly debit by category (based on last 3-6 months history)
#    - Spread that monthly average across the 90-day forecast on a monthly basis
#    This is more realistic and avoids the weekly pattern explosion

import pandas as pd

events_df = pd.read_csv("dataset/financial_events.csv")
u1 = events_df[events_df["user_id"] == "user_01"]
# Settled events only, from last 3 months before request date
req_date = pd.to_datetime("2024-03-03")
start_3m = req_date - pd.Timedelta(days=91)
settled = u1[(u1["status"] == "settled") & 
             (pd.to_datetime(u1["settlement_date"]) >= start_3m) & 
             (pd.to_datetime(u1["settlement_date"]) < req_date)]

print("Monthly averages by category (last 3 months):")
monthly = settled.groupby(["category", "direction"])["amount"].sum() / 3.0
for (cat, d), amt in monthly.items():
    print(f"  {cat} ({d}): {amt:.2f}/month")

# For transport: that would be a monthly bucket
# Salary: next confirmed = 23320 on 2024-03-15
# If we use monthly buckets: each month debit ~categories, credit ~salary
# The 90-day safe amount would be:
# 
# Simple safe = balance - min_balance - projected_net_outflows_over_90_days
# But needs to be the MINIMUM daily balance.
# For monthly debit category model:
#   monthly_debit_total = sum of all debits / 3
#   monthly_credit_total = salary (~23320)
#   net_monthly = monthly_credit - monthly_debit
#   
# Key: does user's balance DROP below min_balance at any point in 90 days?
# If net monthly positive, balance trends upward -> safe
# If net monthly negative, balance trends downward
print("\nSalary events:")
print(u1[(u1["category"] == "salary") | (u1["status"] == "scheduled")][["event_id","description","amount","settlement_date","status"]])
