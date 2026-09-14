import pandas as pd

samples = pd.read_csv('dataset/sample_requests.csv')
for i, r in samples.iterrows():
    print(f"{r['request_id']}: {r['request_type']} {r['requested_amount']} -> safe={r['amount_safe_to_pay']} | {r['affordability_status']} | {r['recommended_payment_method']} | earliest={r['earliest_date_for_full_payment']} | changes={r['spending_changes_needed']}")
