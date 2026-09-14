import pandas as pd
import numpy as np

# Hypothesis: The problem expects ONLY confirmed scheduled events (not recurring projections)
# to be used for cash flow forecasting, PLUS the recurring patterns detected.
# 
# BUT the critical insight: groceries are WEEKLY but we may be miscounting the avg_interval
# because we group by description and average. Let me check: 
# For user_01 groceries - many DIFFERENT descriptions (bulk pantry, fresh food, etc)
# They are all different descriptions so they DON'T group as one recurring rule
# The weekly rule applies to "vehicle charging" which has avg_interval = 7
# Groceries have different descriptions so they would each appear ONCE = no recurring rule
#
# Actually wait - let me trace what our cashflow_model is doing:
# It groups by (description, category, direction) and needs >=2 settled occurrences
# For groceries, each description appears only once or twice
# So most groceries won't be detected as recurring - GOOD
# 
# The problem is the TRANSPORT category - vehicle charging IS detected as weekly
# And it fires heavily in our simulation
#
# Let me count how many times vehicle charging fires in 90 days
req_date = pd.to_datetime("2024-03-03")
last_date = pd.to_datetime("2023-12-16")
count = 0
total = 0
for offset in range(1, 91):
    d = req_date + pd.Timedelta(days=offset)
    if (d - last_date).days % 7 == 0:
        count += 1
        total += 534.56
        print(f"  Vehicle charging on {d.strftime('%Y-%m-%d')}: cumulative {total:.2f}")

print(f"Total vehicle charging in 90 days: {count} times = {total:.2f} ZAR")

# This is TOO MUCH. The user pays vehicle charging weekly = ~534 * 12.8 weeks = 6840 ZAR over 90 days
# That explains why our min_projected drops so much
# 
# But actual behavior: we're firing this EVERY 7 days from the last HISTORICAL date (2023-12-16)
# This means in 90 days starting 2024-03-03, day 1 is 2024-03-04, and:
# 2023-12-16 + N*7 = 2024-03-03 => (2024-03-03 - 2023-12-16) = 77 days, 77/7 = 11 weeks
# So (2024-03-03 + 7 - 2023-12-16) = 84 days from last, 84/7 = 12 => fires on day 7 from req_date
# 
# The key issue: our model fires weekly starting from last_date extended
# But user_01 already paid vehicle charging on 2024-03-02 (event_84 Local taxi, NOT vehicle charging)
# Let me check if there are more recent vehicle charging events we missed
events_df = pd.read_csv("dataset/financial_events.csv")
u1 = events_df[events_df["user_id"] == "user_01"]
transport = u1[u1["category"] == "transport"].sort_values("settlement_date")
print("\nAll transport events for user_01:")
print(transport[["event_id","description","amount","settlement_date","status"]].to_string())
