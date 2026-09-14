import pandas as pd
import numpy as np

# FINAL INSIGHT: Monthly bucket approach
# Monthly debits: 3487 + 306.9 + 2506.61 + 1821.6 + 3360.9 + 235.4 + 5148 + 466.4 + 1911.89 + 1526.58 = 20771.28
# Monthly credits: salary 4275 (historical partial) + 23320 (next) 
# But we should use NEXT CONFIRMED salary = 23320/month
#
# Corrected: net monthly = 23320 - 20771.28 = +2548.72 (POSITIVE - user saves each month)
# 
# For the 90-day simulation starting 2024-03-03:
# Day 0: balance = 58481.1
# Day 12 (March 15): +23320 salary -> 81801.1
# Day 43 (April 15): +23320 salary -> ...
# Day 73 (May 15): +23320 salary
# Monthly expenses: ~20771 per month split across 30 days
# 
# The MINIMUM balance is determined by whether expenses run ahead of salary
# If we spread expenses evenly: each day the balance drops by 20771/30 = 692.37
# By March 15 (12 days): balance drops by 12 * 692 = 8304, to 58481-8304 = 50177
# Then salary +23320 = 73497
# Then over next 30 days to April 15: drops 20771 = 52726 + salary = 76046
# Pattern is growing (net positive)
# 
# WITHOUT payment, min projected is actually around March 15 just before salary:
# 58481.1 - (12/30 * 20771) = 58481.1 - 8308.4 = 50172.7
# that doesn't match 34652.74 from our model...
# 
# OUR MODEL projects weekly expenses which inflate outflows considerably
# The correct monthly outflows should be computed from settled events only in the last period
# 
# APPROACH: Use category-level monthly averages to get a MUCH more realistic forecast
# Key check: does our simple monthly model match the ground truth safe amounts?
# 
# For user_01:
monthly_debits = {
    "debt_repayment": 3487.0,
    "delivery_membership": 306.9,
    "dining": 2506.61,
    "education": 1821.6,
    "groceries": 3360.9,
    "music_subscription": 235.4,
    "rent": 5148.0,
    "shopping": 466.4,
    "transport": 1911.89,
    "utilities": 1526.58,
}
monthly_credits = {
    "salary": 23320.0  # next confirmed salary
}

total_monthly_debit = sum(monthly_debits.values())
total_monthly_credit = sum(monthly_credits.values())
net_monthly = total_monthly_credit - total_monthly_debit
print(f"Monthly debits: {total_monthly_debit:.2f}")
print(f"Monthly credits: {total_monthly_credit:.2f}")
print(f"Net monthly: {net_monthly:.2f}")

# Simulate daily balance using monthly rates
# Assume evenly spread within month
# Special: salary arrives on 15th, rent on 2nd
req_date = pd.to_datetime("2024-03-03")
balance = 58481.1
min_req = 18000
daily_debit = total_monthly_debit / 30.0
daily_credit_non_salary = 0  # salary comes as lump sum

# Next salary: March 15 = 12 days
min_bal = balance
for day in range(91):
    d = req_date + pd.Timedelta(days=day)
    # Deduct daily expenses
    balance -= daily_debit
    # Credit salary on 15th of each month
    if d.day == 15 and day > 0:
        balance += total_monthly_credit
    if balance < min_bal:
        min_bal = balance
        
print(f"\nSimple bucket model: min_balance over 90 days = {min_bal:.2f}")
print(f"Amount safe to pay = {min_bal - min_req:.2f}")
print(f"GT says: 25256.0")
