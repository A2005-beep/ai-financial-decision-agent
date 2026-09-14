import pandas as pd
from engine.image_reader import fill_missing_event_amounts
from engine.fx import FXConverter
from engine.messages_parser import MessageProcessor
from engine.cashflow_model import CashFlowModel
from engine.plan_evaluator import PlanEvaluator

events_df = pd.read_csv('dataset/financial_events.csv')
images_df = pd.read_csv('dataset/images.csv')
profiles_df = pd.read_csv('dataset/financial_profiles.csv')
fx_df = pd.read_csv('dataset/exchange_rates.csv')
messages_df = pd.read_csv('dataset/messages.csv')
options_df = pd.read_csv('dataset/request_payment_options.csv')
samples_df = pd.read_csv('dataset/sample_requests.csv')

# Preprocess
events_df = fill_missing_event_amounts(events_df, images_df)
fx = FXConverter(fx_df)
msg_proc = MessageProcessor(messages_df)
evaluator = PlanEvaluator(fx)

correct_status = 0
correct_method = 0
total = len(samples_df)

for idx, req in samples_df.iterrows():
    u_id = req['user_id']
    u_prof = profiles_df[profiles_df['user_id'] == u_id].iloc[0]
    u_events = events_df[events_df['user_id'] == u_id]
    msg_adj = msg_proc.process_user_messages(u_id, req['request_date'])
    
    model = CashFlowModel(u_prof, u_events, fx, msg_adj)
    model.build(req['request_date'])
    pred = evaluator.evaluate_request(req, u_prof, model, options_df)
    
    match_status = (pred['affordability_status'] == req['affordability_status'])
    match_method = (pred['recommended_payment_method'] == req['recommended_payment_method'])
    if match_status: correct_status += 1
    if match_method: correct_method += 1
    
    print(f"{req['request_id']}: GT=[{req['affordability_status']}, {req['recommended_payment_method']}] | PRED=[{pred['affordability_status']}, {pred['recommended_payment_method']}] | SAFE_GT={req['amount_safe_to_pay']} PRED={pred['amount_safe_to_pay']}")

print(f"\nResults: Status accuracy: {correct_status}/{total} ({correct_status/total*100:.1f}%), Method accuracy: {correct_method}/{total} ({correct_method/total*100:.1f}%)")
