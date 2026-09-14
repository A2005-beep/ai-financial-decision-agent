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

# Debug request_01: user_01, should be affordable_now, safe=25256, but we got 16652.74
# Problem: we're DEDUCTING the pending fuel event, but the problem says "pending debits should be reserved"
# i.e., pending debits ARE already reserved in the balance - or should we treat them?
# Actually: The problem says "Reserve pending debits. Do not count pending credits"
# So pending debits reduce the effective available balance.
# user_01 balance = 58481.1, pending fuel = 567.6, salary scheduled = 23320
# Expected safe = 25256 (full balance), and min_req=18000
# Buffer without payment = 58481.1 - 567.6 (pending debit) + 23320 (scheduled salary) - recurring expenses

# Let's trace exactly day by day for user_01 for 30 days
u_id = 'user_01'
u_prof = profiles_df[profiles_df['user_id'] == u_id].iloc[0]
u_events = events_df[events_df['user_id'] == u_id]
msg_adj = msg_proc.process_user_messages(u_id, '2024-03-03')

model = CashFlowModel(u_prof, u_events, fx, msg_adj)
min_b, daily_b = model.simulate_90_days('2024-03-03')
sorted_days = sorted(daily_b.items())

print(f"Starting balance: {u_prof['current_available_balance']}")
print(f"Minimum required: {u_prof['minimum_balance_to_keep']}")
print(f"Min balance over 90 days: {min_b:.2f}")
print(f"Expected safe_to_pay: {min_b - u_prof['minimum_balance_to_keep']:.2f}")
print(f"\nDay by day (first 20 days):")
for d, b in sorted_days[:20]:
    print(f"  {d}: {b:.2f}")
