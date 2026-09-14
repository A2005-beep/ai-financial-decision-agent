import pandas as pd
import numpy as np

# For user_01, request_01:
# request_date=2024-03-03, requested=25256, expected safe=25256 (affordable_now)
# The ground truth says the user can pay 25256 TODAY (2024-03-03)
#
# Key insight: "amount_safe_to_pay" in the GT is the max safe to pay ON request_date
# INCLUDING the effect of recurring income/expenses within the 90 day window
# 
# The model is producing min_projected = 34652.74 over 90 days WITHOUT payment
# So it correctly identifies safe_buffer = 34652.74 - 18000 = 16652.74
# But GT says 25256...
#
# Let me check if maybe we double-count the March 2 rent 
# event_32 (rent 5148 on 2024-03-02) was ALREADY settled BEFORE request_date
# And event_58 (local market purchase) was on 2024-03-01 - already settled
# The recurring rules find rent re-occurring on day 2 of each month
# So our model would project ANOTHER rent payment on 2024-04-02 which is CORRECT
# 
# But there might be a weekly pattern issue. The vehicle charging is WEEKLY 
# Based on 2023-12-09 and 2023-12-16, it fires every 7 days
# Last date was 2023-12-16. So next firings would be:
# 2023-12-23, 2023-12-30, 2024-01-06, ... 2024-03-02, 2024-03-09 (= 2023-12-16 + 84 days)
# Let's trace this...
last = pd.to_datetime("2023-12-16")
req_d = pd.to_datetime("2024-03-03")
print("Vehicle charging projected dates after request_date:")
cur = last
while (cur - req_d).days < 95:
    if cur >= req_d:
        print(f"  {cur.strftime('%Y-%m-%d')}")
    cur += pd.Timedelta(days=7)

# But we also detect dining, utilities etc as monthly
# The problem: our recurring rules are PROJECTING FUTURE expenditures that don't match ground truth
# Specifically, the groceries are WEEKLY not MONTHLY
# Let me check the detected avg_interval for groceries
events_df = pd.read_csv("dataset/financial_events.csv")
u1 = events_df[events_df["user_id"] == "user_01"]
grocery = u1[(u1["category"] == "groceries") & (u1["status"] == "settled")].sort_values("settlement_date")
print("\nGrocery dates:")
dates = pd.to_datetime(grocery["settlement_date"]).tolist()
for i in range(1, len(dates)):
    print(f"  {dates[i].strftime('%Y-%m-%d')} (interval {(dates[i]-dates[i-1]).days} days, amt={grocery.iloc[i]['amount']})")
