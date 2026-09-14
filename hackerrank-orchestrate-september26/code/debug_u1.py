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

u_id = 'user_01'
u_prof = profiles_df[profiles_df['user_id'] == u_id].iloc[0]
u_events = events_df[events_df['user_id'] == u_id]
msg_adj = msg_proc.process_user_messages(u_id, '2024-03-03')

model = CashFlowModel(u_prof, u_events, fx, msg_adj)
print("Recurring rules detected for user_01:")
for r in model.recurring_rules:
    print(r)

print("\nScheduled events:")
for e in model.scheduled_events:
    print(e)
