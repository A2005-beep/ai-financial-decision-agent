import pandas as pd
from engine.image_reader import fill_missing_event_amounts
from engine.fx import FXConverter
from engine.messages_parser import MessageProcessor
from engine.cashflow_model import CashFlowModel

events_df = pd.read_csv('dataset/financial_events.csv')
images_df = pd.read_csv('dataset/images.csv')
profiles_df = pd.read_csv('dataset/financial_profiles.csv')
fx_df = pd.read_csv('dataset/exchange_rates.csv')
messages_df = pd.read_csv('dataset/messages.csv')
samples_df = pd.read_csv('dataset/sample_requests.csv')

events_df = fill_missing_event_amounts(events_df, images_df)
fx = FXConverter(fx_df)
msg_proc = MessageProcessor(messages_df)

# user_01 expected: safe=25256, status=affordable_now
# Current: safe=16652.74 (16652.74 = min_projected - min_required = 34652.74 - 18000)
# But expected 25256. 
# Key insight: amount_safe_to_pay should be STARTING balance minus min_balance minus reserved pending debits
# The ground truth suggests that the "pending" fuel event should NOT reduce amount_safe_to_pay
# because pending debits are reserved but NOT yet impacting today's balance
# The starting balance already accounts for pending debits in the bank balance
# OR: the scheduled salary should be counted immediately 

# Actually let me re-read: "current_available_balance" is TODAY's available balance.
# The problem says "Reserve pending debits" - meaning we should subtract pending debits from the balance
# But the sample: 58481.1 - 18000 = 40481.1... Still not 25256
# 
# Wait: let me re-read the problem more carefully.
# amount_safe_to_pay: "the most the user can pay TODAY before optional spending changes without breaking 
# the 90-day safety check, capped at requested_amount"
#
# So it's: how much can user pay today AND still keep balance >= min_balance throughout 90 days
# If user pays X today, balance becomes 58481.1 - X
# Then recurring expenses hit, salary comes in etc.
# The minimum over 90 days must be >= 18000
#
# So if min_projected_without_payment = 34652.74 (i.e. balance drops to 34652.74 at some point)
# then safe payment = 34652.74 - 18000 = 16652.74
# But ground truth says 25256 (which is the requested amount - full payment!)
# 
# So the ground truth says amount_safe_to_pay = requested_amount = 25256
# That means min_projected_with_payment of 25256 = 34652.74 - 25256 = 9396.74... that's below 18000!
# 
# WAIT - let me check if the payment is applied ON DAY 0 (the request_date)
# The request_date is 2024-03-03. If user pays 25256 on that day:
# Balance after payment = 58481.1 - 25256 = 33225.1
# Then recurring expenses hit...min would be around 33225.1 - (34652.74-58481.1+18000)... 
# 
# Actually let's compute: without payment min is 34652.74 at some point
# With 25256 payment ON DAY 0, every day's balance is exactly 25256 less
# So min_with_payment = 34652.74 - 25256 = 9396.74 < 18000... FAIL
#
# This means we're WRONG about when the minimum balance occurs.
# The minimum must actually occur BEFORE the salary arrives (2024-03-15)
# And WITH the salary, the balance recovers well above 18000.
# 
# Let me check - is the "pending" debit (567.6) being INCLUDED in available_balance already?
# Banks typically show "available balance" EXCLUDING pending debits
# So the 58481.1 might ALREADY exclude the pending fuel (567.6)
# Therefore we should NOT subtract the pending debit again!

u_id = 'user_01'
u_prof = profiles_df[profiles_df['user_id'] == u_id].iloc[0]
u_events = events_df[events_df['user_id'] == u_id]
msg_adj = msg_proc.process_user_messages(u_id, '2024-03-03')

# Let s trace without pending events
model = CashFlowModel(u_prof, u_events, fx, msg_adj)
print(f"Scheduled events: {model.scheduled_events}")
print(f"\nBalance = 58481.1")
print(f"Without pending fuel (567.6): day min would be ?")
print(f"Current min = 34652.74")
print(f"If pending_fuel is already excluded from balance, day min = 34652.74 + 567.6 = {34652.74 + 567.6:.2f}")

# The amount_safe_to_pay = min_projected - min_balance = (34652.74+567.6) - 18000 = 17220.34... 
# Still not 25256

# DIFFERENT APPROACH: maybe amount_safe_to_pay is computed differently
# Perhaps: safe = starting_balance - min_balance - sum(essential_projected_debits until worst day)
# OR maybe: we should NOT include pending debits at all (they may never settle)
# 
# Let me test WITHOUT pending in simulation:
print(f"\nIf we exclude pending events from simulation:")
print(f"Balance on 2024-03-03: 58481.1")
print(f"March 5: fuel pending 567.6 -> SKIP -> 58481.1")
print(f"March 6: utilities 1386.17 -> 57094.93")
print(f"March 8: education 1821.6 -> 55273.33")
print(f"March 9: vehicle_weekly 534.56 -> 54738.77")
print(f"March 11: debt_repayment 3487 + music 235.4 -> 51016.37")
print(f"March 13: delivery 306.9 -> 50709.47")
print(f"March 14: dining 1017.11 -> 49692.36")
print(f"March 15: salary +23320 = 73012.36")
print(f"...")
print(f"Safe amount = min_projected - 18000")
print(f"Worst day is March 2 (rent): if rent was on March 2 and we are NOW on March 3, rent already hit.")
print(f"Next rent is April 2: bal - 5148 = ?")
print(f"With salary on March 15 and next salary on April 15, need to track through April 2")
print(f"Key: the LOW point before salary is around March 14-15")
print(f"Balance on march 14 without pending = 49692.36")
print(f"Safe = 49692.36 - 18000 = 31692.36 - too high")
print(f"There must be more debits I am missing...")
