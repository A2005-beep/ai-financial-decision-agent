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

# Preprocess
events_df = fill_missing_event_amounts(events_df, images_df)
fx = FXConverter(fx_df)
msg_proc = MessageProcessor(messages_df)

for idx, sample in samples_df.head(5).iterrows():
    u_id = sample['user_id']
    u_prof = profiles_df[profiles_df['user_id'] == u_id].iloc[0]
    u_events = events_df[events_df['user_id'] == u_id]
    msg_adj = msg_proc.process_user_messages(u_id, sample['request_date'])
    
    model = CashFlowModel(u_prof, u_events, fx, msg_adj)
    min_b, daily_b = model.simulate_90_days(sample['request_date'])
    
    print(f"{sample['request_id']}: start_bal={u_prof['current_available_balance']}, min_req={u_prof['minimum_balance_to_keep']}, min_projected={min_b:.2f}, gt_safe={sample['amount_safe_to_pay']}")
